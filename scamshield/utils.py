"""Helper utilities for ScamShield."""
from typing import Iterable


def normalize_text(text: str) -> str:
    """Normalize text for detection: lower, strip, collapse whitespace."""
    return " ".join(text.strip().split()).lower()


def load_lines(path: str) -> Iterable[str]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                yield s
