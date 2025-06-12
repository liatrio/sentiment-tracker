"""Unit tests for report rendering and Slack posting helpers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.reporting.models import ProcessedFeedback
from src.reporting.render import post_report_to_slack, render_report


def _sample_processed() -> ProcessedFeedback:
    return ProcessedFeedback(
        session_id="sess1",
        per_user={},
        all_items=["Great work team!", "Need better comms"],
        sentiment_counts={"positive": 1, "neutral": 0, "negative": 1},
        stats={
            "total_participants": 4,
            "submitted": 2,
            "pending": 2,
            "low_participation": True,
        },
    )


@pytest.fixture()
def processed() -> ProcessedFeedback:
    return _sample_processed()


def test_render_report_basic(processed: ProcessedFeedback):
    with patch(
        "src.reporting.context.anonymize_quotes", side_effect=lambda x: x
    ) as anon_mp, patch(
        "src.reporting.context.extract_themes", return_value=["communication"]
    ) as theme_mp:
        out = render_report(processed)

    anon_mp.assert_called_once()
    theme_mp.assert_called_once()
    assert "sess1" in out
    assert "communication" in out
    # Check emoji presence
    assert "😊" in out and "🙁" in out


def test_post_report_short_message(processed: ProcessedFeedback):
    # Patch renderer to return short text (<2800)
    with patch("src.reporting.render.render_report", return_value="short") as render_mp:
        client = MagicMock()
        post_report_to_slack(processed=processed, client=client, channel="C123")

    render_mp.assert_called_once()
    client.chat_postMessage.assert_called_once_with(channel="C123", text="short")
    client.files_upload.assert_not_called()


def test_post_report_long_upload(processed: ProcessedFeedback):
    long_text = "x" * 3000
    with patch("src.reporting.render.render_report", return_value=long_text):
        client = MagicMock()
        post_report_to_slack(processed=processed, client=client, channel="C123")

    client.files_upload_v2.assert_called_once()
    client.chat_postMessage.assert_not_called()
