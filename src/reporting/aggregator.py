"""Aggregate raw feedback into a structured :class:`ProcessedFeedback`."""

from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from typing import Dict, List

from src.analysis.sentiment import analyze_sentiment
from src.reporting.models import ProcessedFeedback
from src.session_data import SessionData

logger = logging.getLogger(__name__)


def _tally_sentiments(items: List[str]) -> Dict[str, int]:  # pragma: no cover – helper
    """Return a mapping label→count using OpenAI sentiment analysis."""
    counts: Counter[str] = Counter()
    for item in items:
        try:
            result = analyze_sentiment(item)
            counts[result.label.value] += 1
        except Exception as exc:  # noqa: BLE001 – keep going on failures
            logger.warning("Sentiment analysis failed for item: %s", exc)
    return dict(counts)


def process_session(
    session: SessionData,
) -> ProcessedFeedback:  # noqa: C901 – acceptable
    """Convert *session* feedback into :class:`ProcessedFeedback`.

    The function is read-only; it does not mutate *session*.
    """

    # Build per-user mapping (future-proof): we currently cannot guarantee
    # mapping so fall back to a flat list under "unknown".
    per_user: Dict[str, List[str]] = defaultdict(list)
    for item in session.feedback_items:
        per_user["unknown"].append(item)

    all_items: List[str] = list(session.feedback_items)

    sentiment_counts = _tally_sentiments(all_items)

    total_participants = len(session.target_user_ids)
    submitted = len(session.submitted_users)
    pending = len(session.pending_users)

    low_participation = submitted < math.ceil(total_participants / 2)

    stats = {
        "total_participants": total_participants,
        "submitted": submitted,
        "pending": pending,
        "low_participation": low_participation,
    }

    return ProcessedFeedback(
        session_id=session.session_id,
        per_user=dict(per_user),
        all_items=all_items,
        sentiment_counts=sentiment_counts,
        stats=stats,
        reason=session.reason,
    )
