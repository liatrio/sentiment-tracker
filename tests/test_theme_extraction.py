"""Unit tests for extract_themes utility."""
from typing import List

import pytest

from src.analysis import themes as th


@pytest.fixture(autouse=True)
def patch_chat_completion(monkeypatch):
    """Replace OpenAI call with deterministic stub."""

    def _fake_chat(*_, **__):  # type: ignore[override]
        content = '["theme1", "theme2", "theme3"]'
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(th, "chat_completion", _fake_chat)
    yield


def test_extract_themes_basic():
    feedback = [
        "Great teamwork and communication!",
        "We need more transparency on project goals.",
    ]
    result: List[str] = th.extract_themes(feedback, max_themes=3)
    assert result == ["theme1", "theme2", "theme3"]


def test_extract_themes_empty():
    assert th.extract_themes([]) == []
