"""Context dataclass for rendering feedback reports.

This module defines `ReportContext`, a typed container that holds all
values expected by the master Jinja2 template located in
`src/reporting/templates/report.md.j2`.

The separation between *context building* and *template rendering*
enables:
    • Clear contracts between aggregation/analysis logic and Jinja2.
    • Easier unit-testing of business logic without touching template
      strings.
    • Future extension (e.g., HTML or JSON reports) by reusing the same
      context object.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

__all__ = [
    "Stats",
    "ReportContext",
]


@dataclass(slots=True)
class Stats:
    """Basic participation statistics displayed in the report."""

    submitted: int
    total_participants: int
    low_participation: bool = False

    def to_dict(self) -> Dict[str, Any]:  # noqa: D401 – simple helper
        """Return a *plain* ``dict`` representation suitable for Jinja."""
        return asdict(self)


@dataclass(slots=True)
class ReportContext:
    """Container with all fields used by the Slack report template."""

    # Header & meta
    session_id: str
    date: str  # ISO-8601 date string (UTC)

    # Participation & sentiment
    stats: Stats
    emoji_bar: str
    sentiment_counts: Dict[str, int]

    # Analysis outputs
    themes: List[str] = field(default_factory=list)
    bullets_well: List[str] = field(default_factory=list)
    bullets_improve: List[str] = field(default_factory=list)

    # Raw anonymized comments (full list)
    all_items: List[str] = field(default_factory=list)

    # Misc / versioning
    version: str = "1"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:  # noqa: D401 – simple helper
        """Return a *plain* ``dict`` (recursively) for Jinja rendering."""
        return asdict(self)

    # Alias for convenience (e.g. template kwargs)
    __call__ = to_dict
