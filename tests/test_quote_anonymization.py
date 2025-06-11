"""Tests for anonymize_quotes utility."""
from __future__ import annotations

from typing import List

import pytest

from src.analysis import anonymize_quotes as aq


@pytest.fixture(autouse=True)
def patch_chat(monkeypatch):
    """Stub out the OpenAI call with deterministic output."""

    def _fake_chat(*_, **__):  # type: ignore[override]
        # Always return each quote with placeholder replacement
        content = '["redacted 1", "redacted 2"]'
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(aq, "chat_completion", _fake_chat)
    yield


def test_anonymize_basic():
    quotes = [
        "Alice said the deployment was late.",
        "@bob thinks we should refactor the module.",
    ]
    result: List[str] = aq.anonymize_quotes(quotes)
    assert result == ["redacted 1", "redacted 2"]


def test_anonymize_empty():
    assert aq.anonymize_quotes([]) == []
