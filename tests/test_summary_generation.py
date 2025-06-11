"""Tests for generate_summary utility."""
from __future__ import annotations

import pytest

import src.analysis.summary as sm


@pytest.fixture(autouse=True)
def patch_chat(monkeypatch):
    def _fake_chat(*_, **__):  # type: ignore[override]
        return {"choices": [{"message": {"content": "Overall, feedback is positive."}}]}

    monkeypatch.setattr(sm, "chat_completion", _fake_chat)
    yield


def test_generate_summary_normal():
    quotes = ["Great teamwork all around.", "Need clearer deadlines."]
    themes = ["collaboration", "project management"]
    result = sm.generate_summary(quotes, themes)
    assert result == "Overall, feedback is positive."


def test_generate_summary_empty_quotes():
    assert sm.generate_summary([], []) == ""


def test_truncation():
    long_text = "a" * 1000

    def _fake_long(*_, **__):  # type: ignore[override]
        return {"choices": [{"message": {"content": long_text}}]}

    sm.chat_completion = _fake_long  # type: ignore[attr-defined]
    truncated = sm.generate_summary(["foo"], [])
    assert truncated.endswith("…")
    assert len(truncated) <= 901  # <= max_length_chars + ellipsis
