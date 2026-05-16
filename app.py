import base64
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, render_template, request, redirect, url_for

from scraper import discover_site, get_week_schedule, normalize_slug
from visualizer import create_weekly_image, create_day_image
from config import SITE_TIMEZONES

app = Flask(__name__)

_site_cache: dict = {}   # slug → {calendar_id, calendar_name, centers}


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _now_for_site(slug: str) -> datetime:
    tz_name = SITE_TIMEZONES.get(slug)
    try:
        tz = ZoneInfo(tz_name) if tz_name else ZoneInfo("UTC")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


def _get_site(slug: str) -> dict:
    if slug not in _site_cache:
        _site_cache[slug] = discover_site(slug)
    return _site_cache[slug]


def _pool_name(centers: list[dict], center_id: int) -> str:
    return next((c["name"] for c in centers if c["id"] == center_id),
                f"Pool {center_id}")


# ── Landing page ──────────────────────────────────────────────────────────────

@app.route("/")
def landing():
    error = request.args.get("error")
    return render_template("landing.html", error=error)


@app.route("/find", methods=["GET", "POST"])
def find():
    raw = (request.form.get("site") or request.args.get("site") or "").strip()
    if not raw:
        return redirect(url_for("landing"))

    slug = normalize_slug(raw)
    try:
        site = _get_site(slug)
    except ValueError as exc:
        return render_template("landing.html", error=str(exc), prefill=raw)

    centers = site["centers"]
    if len(centers) == 1:
        return redirect(url_for("schedule", site=slug, pool=centers[0]["id"]))

    return render_template("pools.html", site=site, slug=slug)


# ── Schedule views ────────────────────────────────────────────────────────────

@app.route("/schedule")
def schedule():
    slug = request.args.get("site", "").strip()
    if not slug:
        return redirect(url_for("landing"))

    try:
        site = _get_site(slug)
    except ValueError as exc:
        return redirect(url_for("landing", error=str(exc)))

    centers    = site["centers"]
    default_id = centers[0]["id"]
    try:
        center_id = int(request.args.get("pool", default_id))
    except ValueError:
        center_id = default_id

    raw = request.args.get("week", "")
    try:
        ref = datetime.strptime(raw, "%Y-%m-%d").date() if raw else _now_for_site(slug).date()
    except ValueError:
        ref = _now_for_site(slug).date()

    week_start = _week_start(ref)
    week_end   = week_start + timedelta(days=6)
    pool_name  = _pool_name(centers, center_id)

    events    = get_week_schedule(slug, site["calendar_id"], center_id, week_start)
    img_bytes = create_weekly_image(events, pool_name, week_start)
    img_b64   = base64.b64encode(img_bytes).decode("ascii")

    return render_template(
        "schedule.html",
        view       = "week",
        img_b64    = img_b64,
        slug       = slug,
        centers    = centers,
        center_id  = center_id,
        pool_name  = pool_name,
        calendar_name = site["calendar_name"],
        week_start = week_start,
        week_end   = week_end,
        prev_week  = (week_start - timedelta(weeks=1)).isoformat(),
        next_week  = (week_start + timedelta(weeks=1)).isoformat(),
        today_week = _week_start(_now_for_site(slug).date()).isoformat(),
    )


@app.route("/today")
def today_view():
    slug = request.args.get("site", "").strip()
    if not slug:
        return redirect(url_for("landing"))

    try:
        site = _get_site(slug)
    except ValueError as exc:
        return redirect(url_for("landing", error=str(exc)))

    centers    = site["centers"]
    default_id = centers[0]["id"]
    try:
        center_id = int(request.args.get("pool", default_id))
    except ValueError:
        center_id = default_id

    now        = _now_for_site(slug)
    today      = now.date()
    week_start = _week_start(today)
    pool_name  = _pool_name(centers, center_id)
    tz_known   = slug in SITE_TIMEZONES

    events    = get_week_schedule(slug, site["calendar_id"], center_id, week_start)
    img_bytes = create_day_image(
        events, pool_name, today,
        now_minutes=now.hour * 60 + now.minute if tz_known else None,
    )
    img_b64   = base64.b64encode(img_bytes).decode("ascii")

    return render_template(
        "schedule.html",
        view       = "day",
        img_b64    = img_b64,
        slug       = slug,
        centers    = centers,
        center_id  = center_id,
        pool_name  = pool_name,
        calendar_name = site["calendar_name"],
        day_date   = today,
        week_start = week_start,
        week_end   = week_start + timedelta(days=6),
        prev_week  = (week_start - timedelta(weeks=1)).isoformat(),
        next_week  = (week_start + timedelta(weeks=1)).isoformat(),
        today_week = week_start.isoformat(),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
