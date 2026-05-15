import time
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from classifier import classify
from config import SITE_SLUG, CALENDAR_ID, TIMEZONE

_BASE = f"https://anc.apm.activecommunities.com/{SITE_SLUG}/rest/onlinecalendar"
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (PoolRotationSchedule/1.0)",
    "Content-Type": "application/json",
})

_cache: dict = {}
_CACHE_TTL = 3600  # seconds


def get_centers() -> list[dict]:
    """Return [{id, name}, ...] for all pools in the swimming calendar."""
    resp = _SESSION.post(f"{_BASE}/filters", json={"calendar_id": CALENDAR_ID}, timeout=15)
    resp.raise_for_status()
    return resp.json()["body"]["center"]


def get_week_schedule(week_start: date) -> dict[int, list[dict]]:
    """
    Return {center_id: [events]} for the given week.
    Each event: {start, end, title, activity_type, facilities}
    start/end are minutes-from-midnight integers.
    Results cached for one hour.
    """
    cache_key = week_start.isoformat()
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            return data

    centers = get_centers()
    center_ids = [c["id"] for c in centers]
    week_end = week_start + timedelta(days=6)

    resp = _SESSION.post(
        f"{_BASE}/multicenter/events",
        json={
            "calendar_id": CALENDAR_ID,
            "center_ids": center_ids,
            "display_all": 0,
            "search_start_time": week_start.strftime("%m/%d/%Y"),
            "search_end_time": week_end.strftime("%m/%d/%Y"),
            "facility_ids": [],
            "activity_category_ids": [],
            "activity_sub_category_ids": [],
            "activity_ids": [],
            "activity_min_age": None,
            "activity_max_age": None,
            "event_type_ids": [],
        },
        timeout=20,
    )
    resp.raise_for_status()
    raw = resp.json()["body"]["center_events"]

    schedule: dict[int, list[dict]] = {}
    for ce in raw:
        cid = ce["center_id"]
        events = []
        for ev in ce.get("events", []):
            try:
                start_dt = datetime.strptime(ev["start_time"], "%Y-%m-%d %H:%M:%S")
                end_dt   = datetime.strptime(ev["end_time"],   "%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                continue
            # Filter to only events that fall within the requested week
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
        schedule[cid] = events

    _cache[cache_key] = (schedule, time.time())
    return schedule
