"""Data structures for reporting pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class ProcessedFeedback:
    """Normalized feedback data ready for reporting templates."""

    session_id: str
    per_user: Dict[str, List[str]]
    all_items: List[str]
    sentiment_counts: Dict[str, int]
    themes: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def participation_ratio(self) -> float:
        """Return fraction of participants who submitted (0‒1)."""
        submitted = self.stats.get("submitted", 0)
        total = self.stats.get("total_participants", 0) or 1
        return submitted / total
