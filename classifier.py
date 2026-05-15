from enum import Enum


class ActivityType(Enum):
    LAP_SWIM     = "lap_swim"
    OPEN_SWIM    = "open_swim"
    WATER_FITNESS = "water_fitness"
    LESSONS      = "lessons"
    TEAM         = "team"
    CLOSED       = "closed"


COLORS = {
    ActivityType.LAP_SWIM:      "#5DADE2",   # blue
    ActivityType.OPEN_SWIM:     "#52BE80",   # green
    ActivityType.WATER_FITNESS: "#BB8FCE",   # purple
    ActivityType.LESSONS:       "#F0B27A",   # orange
    ActivityType.TEAM:          "#EC7063",   # red
    ActivityType.CLOSED:        "#D5D8DC",   # grey
}

LABELS = {
    ActivityType.LAP_SWIM:      "Lap Swim",
    ActivityType.OPEN_SWIM:     "Open / Rec Swim",
    ActivityType.WATER_FITNESS: "Water Fitness",
    ActivityType.LESSONS:       "Lessons",
    ActivityType.TEAM:          "Team / Masters",
    ActivityType.CLOSED:        "Closed",
}

# Higher value = higher priority when slots overlap
PRIORITY = {
    ActivityType.LAP_SWIM:      5,
    ActivityType.OPEN_SWIM:     4,
    ActivityType.WATER_FITNESS: 3,
    ActivityType.LESSONS:       2,
    ActivityType.TEAM:          1,
    ActivityType.CLOSED:        0,
}

_LAP   = ["lap swim", "emls", "early morning", "adult swim"]
_OPEN  = ["family swim", "recreation swim", "rec swim", "open swim",
          "public swim", "themed swim", "birthday", "party swim"]
_FIT   = ["water fitness", "aqua", "hydro", "water aerobic", "deep water",
          "shallow water", "water zumba"]
_LES   = ["lesson", "learn to swim", "instruction", "beginner",
          "preschool", "toddler", "youth swim", "parent/child", "adaptive"]
_TEAM  = ["team", "masters", "club", "practice", "swim meet",
          "competitive", "triathlon", "synchronized", "water polo"]


def classify(title: str) -> ActivityType:
    t = title.lower()
    if any(k in t for k in _LAP):
        return ActivityType.LAP_SWIM
    if any(k in t for k in _OPEN):
        return ActivityType.OPEN_SWIM
    if any(k in t for k in _FIT):
        return ActivityType.WATER_FITNESS
    if any(k in t for k in _LES):
        return ActivityType.LESSONS
    if any(k in t for k in _TEAM):
        return ActivityType.TEAM
    return ActivityType.CLOSED
