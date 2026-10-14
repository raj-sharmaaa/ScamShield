"""Basic scam detection utilities.

This is a lightweight starter detector using keyword checks and heuristics.
"""
import re
from typing import List

from .config import DEFAULT_SCAM_KEYWORDS

KEYWORD_PATTERN = re.compile(r"\b(" + "|".join(re.escape(k) for k in DEFAULT_SCAM_KEYWORDS) + r")\b", re.IGNORECASE)


def is_scam(text: str, keywords: List[str] = None) -> bool:
    """Return True if text looks like a scam.

    This uses a few heuristics (keyword presence, suspicious short links, and many CAPS).
    It's intentionally simple so it can be extended later.
    """
    if not text:
        return False

    kw_list = keywords or DEFAULT_SCAM_KEYWORDS
    # keyword match
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in kw_list) + r")\b", re.IGNORECASE)
    if pattern.search(text):
        return True

    # suspicious short link patterns
    if re.search(r"https?://(bit\.ly|tinyurl\.com|t\.co|goo\.gl|shrtco\.de)/", text, re.IGNORECASE):
        return True

    # too many uppercase words
    words = re.findall(r"\w+", text)
    if words:
        upper_words = [w for w in words if w.isupper() and len(w) > 1]
        if len(upper_words) / max(1, len(words)) > 0.25:
            return True

    return False
