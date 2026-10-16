import re
from difflib import SequenceMatcher

try:
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False)
except ImportError:
    reader = None

def extract_text(path):
    """Read printed text from a medicine photo. Returns '' if OCR is unavailable."""
    if reader is None:
        return ""
    try:
        result = reader.readtext(path, detail=0)
        return " ".join(result)
    except Exception:
        return ""


def match_medicines(meds, text, min_score=0.7, limit=6):
    """Fuzzy-match OCR text against brand and salt names.
    Returns [(score, medicine), ...] best first."""
    words = set(re.findall(r"[a-z]{4,}", text.lower()))
    scored = []
    for m in meds:
        brand = max((SequenceMatcher(None, m["brand"].lower(), w).ratio() for w in words), default=0)
        salt = max((SequenceMatcher(None, m["salt"].lower(), w).ratio() for w in words), default=0)
        # A printed brand name decides the match; a salt name alone only suggests candidates.
        best = max(brand, min(salt, 0.85))
        if best >= min_score:
            scored.append((round(best, 2), m))
    scored.sort(key=lambda t: -t[0])
    return scored[:limit]
