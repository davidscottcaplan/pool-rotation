DISPLAY_START_MIN = 5 * 60 + 30   # 5:30 AM
DISPLAY_END_MIN   = 21 * 60 + 30  # 9:30 PM
SLOT_MINUTES      = 30

# Known site timezones — used for the NOW marker when timezone is identifiable
SITE_TIMEZONES = {
    "seattle":       "America/Los_Angeles",
    "sfrecpark":     "America/Los_Angeles",
    "portlandparks": "America/Los_Angeles",
    "dprplaymore":   "America/New_York",
    "planoparksandrec": "America/Chicago",
}

# Keywords used to identify the aquatics/swimming calendar on a site
AQUATICS_KEYWORDS = ["swim", "aquatic", "pool", "lap", "water", "natatorium"]
