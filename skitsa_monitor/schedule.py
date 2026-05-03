"""
Field rotation schedule — maps weekday to the discipline for today's Skitsa monitor run.

Monday    → Fashion & Luxury
Tuesday   → Architecture & Design
Wednesday → (no run — AI digest day)
Thursday  → Film & Entertainment
Friday    → Retail & Consumer
"""

from datetime import date


FIELDS = {
    "monday": {
        "name": "Fashion & Luxury",
        "slug": "fashion",
        "lens": "Fashion & Luxury × AI / Marketing",
        "feeds": [
            {"name": "Business of Fashion", "url": "https://www.businessoffashion.com/feed/"},
            {"name": "Vogue Business",       "url": "https://www.voguebusiness.com/feed"},
            {"name": "WWD",                  "url": "https://wwd.com/feed/"},
            {"name": "Glossy",               "url": "https://www.glossy.co/feed/"},
        ],
    },
    "tuesday": {
        "name": "Architecture & Design",
        "slug": "architecture",
        "lens": "Architecture & Design × AI / Marketing",
        "feeds": [
            {"name": "Dezeen",               "url": "https://www.dezeen.com/feed/"},
            {"name": "ArchDaily",            "url": "https://www.archdaily.com/feed/"},
            {"name": "Architectural Digest", "url": "https://www.architecturaldigest.com/feed/rss"},
            {"name": "Archinect",            "url": "https://archinect.com/feed/news/"},
        ],
    },
    "thursday": {
        "name": "Film & Entertainment",
        "slug": "film",
        "lens": "Film & Entertainment × AI / Marketing",
        "feeds": [
            {"name": "Variety",            "url": "https://variety.com/feed/"},
            {"name": "Deadline",           "url": "https://deadline.com/feed/"},
            {"name": "Hollywood Reporter", "url": "https://www.hollywoodreporter.com/feed/"},
            {"name": "IndieWire",          "url": "https://www.indiewire.com/feed/"},
        ],
    },
    "friday": {
        "name": "Retail & Consumer",
        "slug": "retail",
        "lens": "Retail & Consumer × AI / Marketing",
        "feeds": [
            {"name": "Retail Dive",          "url": "https://www.retaildive.com/feeds/news/"},
            {"name": "Modern Retail",        "url": "https://www.modernretail.co/feed/"},
            {"name": "Harvard Business Review", "url": "https://feeds.hbr.org/harvardbusiness"},
            {"name": "Retail TouchPoints",   "url": "https://www.retailtouchpoints.com/feed/"},
        ],
    },
}

_WEEKDAY_MAP = {0: "monday", 1: "tuesday", 3: "thursday", 4: "friday"}


def get_today_field(override: str | None = None) -> dict | None:
    """
    Returns the field config for today's scheduled run.
    Pass override as a slug ('fashion', 'architecture', 'film', 'retail') or
    day name ('monday', etc.) to force a specific field regardless of date.
    Returns None on unscheduled days (Wednesday, weekends) unless override is set.
    """
    if override:
        key = override.lower()
        # Accept either slug or day name
        if key in FIELDS:
            return FIELDS[key]
        for day_name, config in FIELDS.items():
            if config["slug"] == key:
                return config
        return None

    weekday = date.today().weekday()  # 0=Monday … 6=Sunday
    day_name = _WEEKDAY_MAP.get(weekday)
    if day_name is None:
        return None
    return FIELDS[day_name]
