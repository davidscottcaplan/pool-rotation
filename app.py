import base64
import os
from datetime import date, datetime, timedelta

from flask import Flask, render_template, request

from scraper import get_centers, get_week_schedule
from visualizer import create_weekly_image, create_day_image
from config import TIMEZONE

app = Flask(__name__)
_centers_cache: list[dict] | None = None


def _get_centers() -> list[dict]:
    global _centers_cache
    if _centers_cache is None:
        _centers_cache = get_centers()
    return _centers_cache


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _now_eastern() -> datetime:
    return datetime.now(TIMEZONE)


@app.route("/")
def index():
    centers = _get_centers()
    default_center = centers[0]["id"]

    try:
        center_id = int(request.args.get("pool", default_center))
    except ValueError:
        center_id = default_center

    raw = request.args.get("week", "")
    try:
        ref = datetime.strptime(raw, "%Y-%m-%d").date() if raw else _now_eastern().date()
    except ValueError:
        ref = _now_eastern().date()

    week_start = _week_start(ref)
    week_end   = week_start + timedelta(days=6)

    pool_name = next((c["name"] for c in centers if c["id"] == center_id),
                     f"Pool {center_id}")

    schedule  = get_week_schedule(week_start)
    img_bytes = create_weekly_image(schedule, center_id, pool_name, week_start)
    img_b64   = base64.b64encode(img_bytes).decode("ascii")

    return render_template(
        "index.html",
        view       = "week",
        img_b64    = img_b64,
        centers    = centers,
        center_id  = center_id,
        pool_name  = pool_name,
        week_start = week_start,
        week_end   = week_end,
        prev_week  = (week_start - timedelta(weeks=1)).isoformat(),
        next_week  = (week_start + timedelta(weeks=1)).isoformat(),
        today_week = _week_start(_now_eastern().date()).isoformat(),
    )


@app.route("/today")
def today_view():
    centers = _get_centers()
    default_center = centers[0]["id"]

    try:
        center_id = int(request.args.get("pool", default_center))
    except ValueError:
        center_id = default_center

    now        = _now_eastern()
    today      = now.date()
    week_start = _week_start(today)
    pool_name  = next((c["name"] for c in centers if c["id"] == center_id),
                      f"Pool {center_id}")

    schedule  = get_week_schedule(week_start)
    all_evs   = schedule.get(center_id, [])

    img_bytes = create_day_image(all_evs, pool_name, today,
                                 now_minutes=now.hour * 60 + now.minute)
    img_b64   = base64.b64encode(img_bytes).decode("ascii")

    return render_template(
        "index.html",
        view       = "day",
        img_b64    = img_b64,
        centers    = centers,
        center_id  = center_id,
        pool_name  = pool_name,
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
