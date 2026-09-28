"""Detect spoken trigger phrases such as "visualize this"."""
from __future__ import annotations

import re
import time

TRIGGER_PATTERNS = [
    r"\bvisuali[sz]e\s+(this|that|it)(\s+(line|concept|slide|part|page|diagram))?\b",
    r"\bvisuali[sz]e\s+the\s+(slide|whole\s+page|whole\s+slide|page|concept|line)\b",
    r"\bshow\s+me\s+a\s+diagram\b",
    r"\bdraw\s+this\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in TRIGGER_PATTERNS]


class TriggerDetector:
    """Returns the matched phrase, or None. Debounced so one sentence fires once."""

    def __init__(self, cooldown_seconds: float = 8.0):
        self.cooldown = cooldown_seconds
        self._last_fire = float("-inf")
        self._last_text = ""

    def check(self, text: str, now: float | None = None) -> str | None:
        now = time.monotonic() if now is None else now
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        for pattern in _COMPILED:
            match = pattern.search(normalized)
            if match:
                if now - self._last_fire < self.cooldown or normalized == self._last_text:
                    return None
                self._last_fire, self._last_text = now, normalized
                return match.group(0)
        return None
