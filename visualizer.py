import io
import math
from datetime import date, timedelta
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

from classifier import ActivityType, COLORS, LABELS, PRIORITY
from config import DISPLAY_START_MIN, DISPLAY_END_MIN, SLOT_MINUTES

N_SLOTS = (DISPLAY_END_MIN - DISPLAY_START_MIN) // SLOT_MINUTES
COLOR_CLOSED = COLORS[ActivityType.CLOSED]

# Integer grid value for each ActivityType
_TYPE_INT = {t: i for i, t in enumerate(ActivityType)}
_INT_TYPE = {i: t for t, i in _TYPE_INT.items()}
_N_TYPES  = len(ActivityType)
_CMAP     = mcolors.ListedColormap([COLORS[_INT_TYPE[i]] for i in range(_N_TYPES)])
_NORM     = mcolors.BoundaryNorm(range(_N_TYPES + 1), _CMAP.N)


def _slot_to_label(slot: int) -> str:
    total  = DISPLAY_START_MIN + slot * SLOT_MINUTES
    h, m   = divmod(total, 60)
    period = "AM" if h < 12 else "PM"
    h12    = h % 12 or 12
    return f"{h12}:{m:02d} {period}"


def _build_day_grid(day_events: list[dict]) -> np.ndarray:
    """Return (N_SLOTS,) int array of best ActivityType per slot."""
    grid = np.full(N_SLOTS, _TYPE_INT[ActivityType.CLOSED], dtype=int)
    for ev in day_events:
        s0 = (ev["start"] - DISPLAY_START_MIN) // SLOT_MINUTES
        s1 = math.ceil((ev["end"] - DISPLAY_START_MIN) / SLOT_MINUTES)
        atype = ev["activity_type"]
        val   = _TYPE_INT[atype]
        pri   = PRIORITY[atype]
        for s in range(max(0, s0), min(N_SLOTS, s1)):
            cur_pri = PRIORITY[_INT_TYPE[grid[s]]]
            if pri > cur_pri:
                grid[s] = val
    return grid


def _legend_patches() -> list:
    return [
        mpatches.Patch(color=COLORS[t], label=LABELS[t])
        for t in ActivityType
        if t != ActivityType.CLOSED
    ]


def create_weekly_image(
    schedule: dict[int, list[dict]],
    center_id: int,
    pool_name: str,
    week_start: date,
) -> bytes:
    week_end  = week_start + timedelta(days=6)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    fig, axes = plt.subplots(
        1, 7, figsize=(18, 9), sharey=True,
        gridspec_kw={"wspace": 0.04},
    )

    fig.text(0.5, 0.99, f"{pool_name} — Activity Schedule",
             ha="center", va="top", fontsize=13, fontweight="bold")

    all_events = schedule.get(center_id, [])

    for day_idx in range(7):
        ax  = axes[day_idx]
        day = (week_start + timedelta(days=day_idx)).isoformat()
        day_evs = [e for e in all_events if e["date"] == day]
        grid = _build_day_grid(day_evs).reshape(-1, 1)

        ax.pcolormesh(grid, cmap=_CMAP, norm=_NORM,
                      edgecolors="white", linewidth=0.3)
        ax.set_xlim(0, 1)
        ax.set_ylim(N_SLOTS, 0)
        ax.set_title(
            f"{day_names[day_idx]}\n{(week_start + timedelta(days=day_idx)).strftime('%b %-d')}",
            fontsize=9, pad=4,
        )
        ax.set_xticks([])
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)
            spine.set_color("#aaaaaa")

    ax0 = axes[0]
    hour_ticks = list(range(0, N_SLOTS + 1, 2))
    ax0.set_yticks(hour_ticks)
    ax0.set_yticklabels([_slot_to_label(t) for t in hour_ticks], fontsize=7)
    ax0.yaxis.set_tick_params(length=2, pad=2)
    ax0.set_ylabel("Time of Day", fontsize=9, labelpad=4)

    fig.legend(
        handles=_legend_patches(),
        loc="lower center", ncol=len(ActivityType) - 1,
        fontsize=8, frameon=False,
        bbox_to_anchor=(0.5, 0.0),
    )

    week_label = (f"Week of {week_start.strftime('%B %-d')}–"
                  f"{week_end.strftime('%-d, %Y')}")
    fig.text(0.5, 0.03, week_label, ha="center", fontsize=10, style="italic")

    plt.subplots_adjust(top=0.91, bottom=0.10, left=0.06, right=0.99)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def create_day_image(
    all_events: list[dict],
    pool_name: str,
    day_date: date,
    now_minutes: Optional[int] = None,
) -> bytes:
    day_evs = [e for e in all_events if e["date"] == day_date.isoformat()]
    grid = _build_day_grid(day_evs).reshape(-1, 1)

    fig, ax = plt.subplots(figsize=(7, 11))

    ax.pcolormesh(grid, cmap=_CMAP, norm=_NORM,
                  edgecolors="white", linewidth=0.6)

    # Event labels
    seen = set()
    for ev in day_evs:
        key = (ev["start"], ev["end"], ev["title"])
        if key in seen:
            continue
        seen.add(key)
        s0 = (ev["start"] - DISPLAY_START_MIN) / SLOT_MINUTES
        s1 = math.ceil((ev["end"] - DISPLAY_START_MIN) / SLOT_MINUTES)
        span = s1 - s0
        if span < 0.8:
            continue
        # Shorten label
        label = ev["title"].replace(" - Drop In", "").replace(" - Drop-In", "")
        fontsize = min(7.5, max(5.5, span * 2.0))
        ax.text(0.5, (s0 + s1) / 2, label,
                ha="center", va="center", fontsize=fontsize,
                color="#222222", clip_on=True)

    # NOW marker
    if now_minutes is not None and DISPLAY_START_MIN <= now_minutes <= DISPLAY_END_MIN:
        now_slot = (now_minutes - DISPLAY_START_MIN) / SLOT_MINUTES
        ax.axhline(now_slot, color="#e53e3e", linewidth=2.5, zorder=5)
        h, m  = divmod(now_minutes, 60)
        period = "AM" if h < 12 else "PM"
        h12    = h % 12 or 12
        ax.text(0.97, now_slot - 0.25, f"NOW  {h12}:{m:02d} {period}",
                ha="right", va="bottom", fontsize=7.5,
                color="#e53e3e", fontweight="bold", zorder=6,
                transform=ax.get_yaxis_transform())

    ax.set_xlim(0, 1)
    ax.set_ylim(N_SLOTS, 0)
    ax.set_xticks([])

    all_ticks = list(range(0, N_SLOTS + 1))
    ax.set_yticks(all_ticks)
    ax.set_yticklabels([_slot_to_label(t) for t in all_ticks], fontsize=7.5)
    ax.yaxis.set_tick_params(length=2, pad=3)
    ax.set_ylabel("Time of Day", fontsize=10, labelpad=6)

    for spine in ax.spines.values():
        spine.set_linewidth(0.5)
        spine.set_color("#aaaaaa")

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    fig.suptitle(
        f"{pool_name}\n{day_names[day_date.weekday()]} {day_date.strftime('%B %-d, %Y')}",
        fontsize=12, fontweight="bold", y=0.995,
    )

    fig.legend(
        handles=_legend_patches(),
        loc="lower center", ncol=3,
        fontsize=8, frameon=False,
        bbox_to_anchor=(0.5, 0.0),
    )

    plt.subplots_adjust(top=0.94, bottom=0.12, left=0.15, right=0.97)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
