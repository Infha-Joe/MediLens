import math
import re

_RANGE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:-|–|to)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)


def haversine_km(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


def _mins(h, m, ap):
    h, m = int(h), int(m or 0)
    if ap:
        if not 1 <= h <= 12:
            return None
        h = h % 12 + (12 if ap.lower() == "pm" else 0)
    elif h > 23:
        return None
    return h * 60 + m


def is_open(hours, now):
    """True/False from text like '9:00 AM - 9:00 PM' or '24 hours'; None if unclear."""
    text = hours or ""
    if re.search(r"24\s*(h|hr|hrs|hours)\b|24\s*[x*/]\s*7", text, re.I):
        return True
    m = _RANGE.search(text)
    if not m:
        return None
    h1, m1, a1, h2, m2, a2 = m.groups()
    if not (a1 and a2) and not (int(h1) > 12 or int(h2) > 12):
        return None  # "9-9" is ambiguous
    s, e = _mins(h1, m1, a1), _mins(h2, m2, a2)
    if s is None or e is None:
        return None
    t = now.hour * 60 + now.minute
    return s <= t < e if s < e else (t >= s or t < e)
