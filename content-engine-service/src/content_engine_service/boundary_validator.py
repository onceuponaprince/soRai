from __future__ import annotations

import re

from content_engine_service.run_types import BoundaryStatus, BoundaryVerdict


class BoundaryRejected(Exception):
    def __init__(self, verdict: BoundaryVerdict) -> None:
        super().__init__(verdict.detail)
        self.verdict = verdict


_REFUSE_PATTERNS = (
    re.compile(r"\bminor(s)?\b", re.IGNORECASE),
    re.compile(r"\bunder[- ]?age\b", re.IGNORECASE),
    re.compile(r"\bwithout consent\b", re.IGNORECASE),
    re.compile(r"\bassault\b", re.IGNORECASE),
)

_REJECT_PATTERNS = (
    re.compile(r"\bignore previous instructions\b", re.IGNORECASE),
    re.compile(r"\bignore (?:the )?scope[- ]?guard\b", re.IGNORECASE),
    re.compile(r"\bpornographic\b", re.IGNORECASE),
    re.compile(r"\bexplicit sexual\b", re.IGNORECASE),
)


def sanitize_for_boundary(output: str) -> str:
    marker = "===== FILE:"
    text = output or ""
    if marker in text:
        head = text.split(marker, 1)[0].strip()
        if head:
            return head
    return text.strip()


def validate(output: str, profile: str) -> BoundaryVerdict:
    text = sanitize_for_boundary(output)
    if "__BOUNDARY_FAIL__" in text:
        return BoundaryVerdict(BoundaryStatus.REJECT_EXPLICIT, f"{profile}: test tripwire matched")

    for pattern in _REFUSE_PATTERNS:
        if pattern.search(text):
            return BoundaryVerdict(BoundaryStatus.REFUSE_AND_STOP, f"{profile}: refuse boundary matched {pattern.pattern!r}")

    for pattern in _REJECT_PATTERNS:
        if pattern.search(text):
            return BoundaryVerdict(BoundaryStatus.REJECT_EXPLICIT, f"{profile}: reject boundary matched {pattern.pattern!r}")

    return BoundaryVerdict(BoundaryStatus.PASS, f"{profile}: passed boundary validation")
