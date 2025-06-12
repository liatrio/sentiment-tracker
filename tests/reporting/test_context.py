"""Unit tests for ReportContext dataclass."""
from __future__ import annotations

from src.reporting.context import ReportContext, Stats


def _sample_context() -> ReportContext:
    stats = Stats(submitted=3, total_participants=5, low_participation=False)
    return ReportContext(
        session_id="sess-1",
        date="2025-06-12",
        stats=stats,
        emoji_bar="😀😀😐",
        sentiment_counts={"positive": 2, "neutral": 1, "negative": 0},
        themes=["foo", "bar"],
        bullets_well=["• did X well"],
        bullets_improve=["• could improve Y"],
        all_items=["Some anonymized quote"],
        version="1",
    )


def test_to_dict_roundtrip() -> None:
    """`to_dict` should faithfully convert to nested dict and alias __call__."""
    ctx = _sample_context()
    as_dict = ctx.to_dict()

    # Basic fields
    assert as_dict["session_id"] == ctx.session_id
    assert as_dict["date"] == ctx.date
    assert as_dict["emoji_bar"] == ctx.emoji_bar
    assert as_dict["sentiment_counts"] == ctx.sentiment_counts

    # Nested stats
    stats_dict = as_dict["stats"]
    assert stats_dict == ctx.stats.to_dict()

    # Alias `__call__` returns same mapping
    assert ctx() == as_dict


def test_default_lists_are_empty() -> None:
    """When optional fields are omitted they should default to empty lists."""
    ctx = ReportContext(
        session_id="sess-2",
        date="2025-06-12",
        stats=Stats(submitted=0, total_participants=10),
        emoji_bar="",
        sentiment_counts={},
    )

    assert ctx.themes == []
    assert ctx.bullets_well == []
    assert ctx.bullets_improve == []
    assert ctx.all_items == []

    # Ensure dict conversion still contains those keys as lists
    d = ctx.to_dict()
    assert d["themes"] == []
    assert d["bullets_well"] == []
    assert d["all_items"] == []
