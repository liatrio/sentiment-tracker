"""Unit tests for reporting.aggregator.

Mocks sentiment analysis to ensure deterministic behaviour.
"""

from __future__ import annotations

from unittest.mock import patch

from src.analysis.sentiment import SentimentLabel, SentimentResult
from src.reporting.aggregator import process_session
from src.session_data import SessionData


def _make_session(
    total: int, submitted_count: int, feedback_texts: list[str]
):  # helper
    participants = [f"U{i}" for i in range(total)]
    session = SessionData(
        session_id="S123",
        initiator_user_id="U0",
        channel_id="C1",
        target_user_ids=participants,
    )
    submitted_users = set(participants[:submitted_count])
    session.submitted_users.update(submitted_users)
    session.pending_users -= submitted_users
    session.feedback_items.extend(feedback_texts)
    return session


class _SentimentIter:
    """Helper to yield predefined sentiment results in sequence."""

    def __init__(self, labels: list[str]):
        self._labels = labels
        self._idx = 0

    def __call__(self, _text: str):
        label = self._labels[self._idx % len(self._labels)]
        self._idx += 1
        return SentimentResult(label=SentimentLabel(label), score=0.9)


@patch("src.reporting.aggregator.analyze_sentiment")
def test_process_session_happy_path(mock_analyze):
    """Sentiment counts and stats are calculated correctly."""

    labels = ["positive", "negative", "neutral"]
    mock_analyze.side_effect = _SentimentIter(labels)

    session = _make_session(4, 3, ["Text1", "Text2", "Text3"])
    processed = process_session(session)

    assert processed.stats["submitted"] == 3
    assert processed.stats["pending"] == 1
    assert processed.stats["low_participation"] is False

    # Sentiment counts should reflect our side_effect labels order
    assert processed.sentiment_counts == {
        "positive": 1,
        "negative": 1,
        "neutral": 1,
    }


@patch("src.reporting.aggregator.analyze_sentiment")
def test_low_participation_flag(mock_analyze):
    """Low participation flagged when submissions < ceil(total/2)."""

    mock_analyze.side_effect = _SentimentIter(["neutral", "neutral"])

    session = _make_session(5, 2, ["A", "B"])
    processed = process_session(session)

    assert processed.stats["submitted"] == 2
    assert processed.stats["low_participation"] is True


@patch("src.reporting.aggregator.analyze_sentiment")
def test_empty_feedback_safe(mock_analyze):
    """Aggregator handles sessions with no feedback gracefully."""

    mock_analyze.side_effect = AssertionError("Should not be called")

    session = _make_session(3, 0, [])
    processed = process_session(session)

    assert processed.all_items == []
    assert processed.sentiment_counts == {}
    assert processed.stats["submitted"] == 0
    assert processed.stats["low_participation"] is True
