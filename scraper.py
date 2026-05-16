import re
import time
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import requests

from classifier import classify
from config import AQUATICS_KEYWORDS

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (PoolRotationSchedule/1.0)",
    "Content-Type": "application/json",
})

_cache: dict = {}
_CACHE_TTL = 3600


# ── Slug normalisation ────────────────────────────────────────────────────────

def normalize_slug(raw: str) -> str:
    """
    Accept a bare slug ('seattle') or any ActiveNet URL and return the slug.
    e.g. https://apm.activecommunities.com/seattle/ActiveNet_Calendar → 'seattle'
         https://anc.apm.activecommunities.com/sfrecpark/rest          → 'sfrecpark'
    """
    raw = raw.strip().rstrip("/")
    if "activecommunities.com" in raw or "activenetwork.com" in raw:
        parsed = urlparse(raw if raw.startswith("http") else "https://" + raw)
        parts = [p for p in parsed.path.split("/") if p]
        if parts:
            return parts[0].lower()
    # Plain slug — strip any trailing path junk
    slug = re.split(r"[/?#]", raw)[0].lower()
    return slug


def _base(slug: str) -> str:
    return f"https://anc.apm.activecommunities.com/{slug}/rest/onlinecalendar"


# ── Site discovery ────────────────────────────────────────────────────────────

def discover_site(raw_input: str) -> dict:
    """
    Probe an ActiveNet site and return its aquatics calendar + pool list.
    Returns:
        {slug, calendar_id, calendar_name, centers: [{id, name}]}
    Raises ValueError with a human-readable message on failure.
    """
    slug = normalize_slug(raw_input)
    base = _base(slug)

    try:
        resp = _SESSION.get(f"{base}/calendars", timeout=12)
    except requests.RequestException as exc:
        raise ValueError(f"Could not reach '{slug}' — check the URL and try again.") from exc

    if resp.status_code == 404:
        raise ValueError(f"No ActiveNet site found for '{slug}'.")
    if not resp.ok:
        raise ValueError(f"Site '{slug}' returned an error ({resp.status_code}).")

    try:
        calendars = resp.json()["body"]["calendars"]
    except (KeyError, ValueError):
        raise ValueError(f"'{slug}' doesn't look like an ActiveNet site.")

    # Find the aquatics calendar
    aquatics = None
    for cal in calendars:
        name = cal.get("name", "").lower()
        if any(kw in name for kw in AQUATICS_KEYWORDS):
            aquatics = cal
            break

    if aquatics is None:
        names = [c.get("name", "") for c in calendars]
        raise ValueError(
            f"No swimming/aquatics calendar found on '{slug}'. "
            f"Available calendars: {', '.join(names) or 'none'}."
        )

    calendar_id = aquatics["calendar_id"]

    # Get pool list for this calendar
    try:
        f_resp = _SESSION.post(f"{base}/filters",
                               json={"calendar_id": calendar_id}, timeout=12)
        f_resp.raise_for_status()
        centers = f_resp.json()["body"]["center"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise ValueError(f"Could not load pools for '{slug}'.") from exc

    if not centers:
        raise ValueError(f"No pools found in the '{aquatics['name']}' calendar on '{slug}'.")

    return {
        "slug":          slug,
        "calendar_id":   calendar_id,
        "calendar_name": aquatics["name"],
        "centers":       centers,
    }


# ── Schedule fetching ─────────────────────────────────────────────────────────

def get_week_schedule(slug: str, calendar_id: int, center_id: int,
                      week_start: date) -> list[dict]:
    """
    Return a list of events for one pool for the given week.
    Each event: {date, start, end, title, activity_type, facilities}
    Cached for one hour per (slug, center_id, week).
    """
    cache_key = (slug, center_id, week_start.isoformat())
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            return data

    week_end = week_start + timedelta(days=6)
    base = _base(slug)

    resp = _SESSION.post(
        f"{base}/multicenter/events",
        json={
            "calendar_id":              calendar_id,
            "center_ids":               [center_id],
            "display_all":              0,
            "search_start_time":        week_start.strftime("%m/%d/%Y"),
            "search_end_time":          week_end.strftime("%m/%d/%Y"),
            "facility_ids":             [],
            "activity_category_ids":    [],
            "activity_sub_category_ids": [],
            "activity_ids":             [],
            "activity_min_age":         None,
            "activity_max_age":         None,
            "event_type_ids":           [],
        },
        timeout=20,
    )
    resp.raise_for_status()

    events = []
    for ce in resp.json()["body"]["center_events"]:
        if ce["center_id"] != center_id:
            continue
        for ev in ce.get("events", []):
            try:
                start_dt = datetime.strptime(ev["start_time"], "%Y-%m-%d %H:%M:%S")
                end_dt   = datetime.strptime(ev["end_time"],   "%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                continue
            ev_date = start_dt.date()
            if not (week_start <= ev_date <= week_end):
                continue
            events.append({
                "date":          ev_date.isoformat(),
                "start":         start_dt.hour * 60 + start_dt.minute,
                "end":           end_dt.hour * 60 + end_dt.minute,
                "title":         ev.get("title", ""),
                "activity_type": classify(ev.get("title", "")),
                "facilities":    [f["facility_name"] for f in ev.get("facilities", [])],
            })

    _cache[cache_key] = (events, time.time())
    return events
