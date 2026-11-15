"""Small safety measures around the AI step. They are deliberately simple and honest
about their limits: they reduce risk, they do not remove it.

- mask_personal_data: replaces e-mail addresses, IBANs, card-like numbers and phone
  numbers before a description is sent to the AI. It cannot find names or addresses.
- looks_like_instructions: spots text that tries to give orders to the AI.
- RateLimiter: caps how often the paid AI endpoints can be called.
"""
from __future__ import annotations

import re
import time
from collections import deque

# ---- personal data ----------------------------------------------------------------

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b")
_CARD = re.compile(r"(?<![\w.])\d(?:[ -]?\d){12,18}(?![\w])")
_PHONE = re.compile(r"(?<![\w.])(?:\+|00|0)\d[\d ()/\-]{6,}\d(?!\w)")


def _luhn_ok(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _iban_ok(text: str) -> bool:
    compact = text.replace(" ", "")
    if not 15 <= len(compact) <= 34:
        return False
    rearranged = compact[4:] + compact[:4]
    number = "".join(str(int(char, 36)) for char in rearranged)
    return int(number) % 97 == 1


def mask_personal_data(text: str) -> tuple[str, dict]:
    """The text with personal data replaced by [EMAIL], [IBAN], [CARD] and [PHONE],
    and how many of each were found. Counts only, never the values."""
    counts = {"email": 0, "iban": 0, "card": 0, "phone": 0}

    def replace(kind, label, check=None):
        def inner(match):
            if check and not check(match.group()):
                return match.group()
            counts[kind] += 1
            return label
        return inner

    text = _EMAIL.sub(replace("email", "[EMAIL]"), text)
    text = _IBAN.sub(replace("iban", "[IBAN]", _iban_ok), text)
    text = _CARD.sub(replace("card", "[CARD]", lambda m: _luhn_ok(re.sub(r"\D", "", m))), text)
    text = _PHONE.sub(replace("phone", "[PHONE]", lambda m: 8 <= len(re.sub(r"\D", "", m)) <= 15), text)
    return text, {kind: n for kind, n in counts.items() if n}


# ---- instruction-like text --------------------------------------------------------

_INSTRUCTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:instructions?|rules?|prompts?|above|previous|prior)\b",
    r"\b(?:system|developer)\s+(?:prompt|message|instructions?)\b",
    r"\byou\s+are\s+now\b",
    r"\bnew\s+instructions?\b",
    r"\b(?:reveal|show|print|repeat)\b[^.\n]{0,30}\b(?:prompt|instructions?|api[ -]?key|secret)\b",
    r"\b(?:jailbreak|developer\s+mode|do\s+anything\s+now)\b",
    r"\bdo\s+not\s+follow\b[^.\n]{0,30}\b(?:rules?|instructions?)\b",
    r"\banswer\s+with\s+(?:only\s+)?(?:true|false|yes|no)\s+for\s+every\b",
)]


def looks_like_instructions(text: str) -> bool:
    return any(pattern.search(text) for pattern in _INSTRUCTION_PATTERNS)


# ---- rate limit -------------------------------------------------------------------

class RateLimiter:
    """At most `per_client` calls per client and `overall` calls in total per window.
    In memory, so it resets when the service restarts and is per process."""

    def __init__(self, per_client: int, overall: int, window: float = 60.0, clock=time.monotonic):
        self.per_client, self.overall, self.window, self._clock = per_client, overall, window, clock
        self._hits: dict[str, deque] = {}

    def _prune(self, queue: deque, now: float) -> None:
        while queue and now - queue[0] >= self.window:
            queue.popleft()

    def check(self, client: str) -> float | None:
        """None if the call is allowed (and counted), else the seconds to wait."""
        now = self._clock()
        if len(self._hits) > 1000:
            for key in [k for k, q in self._hits.items() if not q or now - q[-1] >= self.window]:
                del self._hits[key]
        everyone = self._hits.setdefault("*", deque())
        mine = self._hits.setdefault("c:" + client, deque())
        self._prune(everyone, now)
        self._prune(mine, now)
        for queue, limit in ((mine, self.per_client), (everyone, self.overall)):
            if len(queue) >= limit:
                return max(1.0, self.window - (now - queue[0]))
        mine.append(now)
        everyone.append(now)
        return None
