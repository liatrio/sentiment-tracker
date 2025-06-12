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


def test_build_report_context(monkeypatch):
    """build_report_context should assemble fields and respect limits."""

    from src.reporting.context import build_report_context
    from src.reporting.models import ProcessedFeedback

    # Patch external helpers to deterministic output
    monkeypatch.setattr("src.reporting.context.anonymize_quotes", lambda items: items)
    monkeypatch.setattr(
        "src.reporting.context.extract_themes",
        lambda items: ["teamwork", "communication"],
    )

    processed = ProcessedFeedback(
        session_id="sess42",
        per_user={},
        all_items=[f"item {i}" for i in range(10)],
        sentiment_counts={"positive": 5, "neutral": 3, "negative": 2},
        stats={
            "submitted": 5,
            "total_participants": 8,
            "low_participation": False,
        },
    )

    ctx = build_report_context(processed)

    # Basic asserts
    assert ctx.session_id == "sess42"
    assert len(ctx.themes) <= 5  # obey MAX_THEMES
    assert ctx.stats.submitted == 5
    # Emoji bar length <= MAX_EMOJI_BAR
    from src.reporting import config as _cfg

    assert len(ctx.emoji_bar) <= _cfg.MAX_EMOJI_BAR
    # Bullets list should obey cap (even if empty in this synthetic data)
    assert len(ctx.bullets_well) <= _cfg.MAX_BULLETS_EACH
    assert len(ctx.bullets_improve) <= _cfg.MAX_BULLETS_EACH


def _make_items(num: int) -> list[str]:
    """Generate mock feedback items with well/improve markers."""

    return [f"well=good {i}, improve=bad {i}" for i in range(num)]


def test_truncation_and_order(monkeypatch):
    """Bullets lists should be truncated to configured maximum and preserve order."""

    from src.reporting import config as _cfg
    from src.reporting.context import build_report_context
    from src.reporting.models import ProcessedFeedback

    monkeypatch.setattr("src.reporting.context.anonymize_quotes", lambda items: items)
    monkeypatch.setattr("src.reporting.context.extract_themes", lambda items: [])

    # Over-provide 10 items (> default 5)
    items = _make_items(10)

    processed = ProcessedFeedback(
        session_id="sess99",
        per_user={},
        all_items=items,
        sentiment_counts={"positive": 1},
        stats={"submitted": 10, "total_participants": 10, "low_participation": False},
    )

    ctx = build_report_context(processed)

    assert ctx.bullets_well == [f"• good {i}" for i in range(_cfg.MAX_BULLETS_EACH)]
    assert ctx.bullets_improve == [f"• bad {i}" for i in range(_cfg.MAX_BULLETS_EACH)]


def test_low_participation_flag(monkeypatch):
    """Low-participation flag should propagate to stats in context."""

    from src.reporting.context import build_report_context
    from src.reporting.models import ProcessedFeedback

    monkeypatch.setattr("src.reporting.context.anonymize_quotes", lambda items: items)
    monkeypatch.setattr("src.reporting.context.extract_themes", lambda items: [])

    processed = ProcessedFeedback(
        session_id="sess-low",
        per_user={},
        all_items=[],
        sentiment_counts={},
        stats={"submitted": 1, "total_participants": 10, "low_participation": True},
    )

    ctx = build_report_context(processed)

    assert ctx.stats.low_participation is True
