"""Unit tests for extract_themes utility."""
import sys
from typing import List

import pytest

from src.analysis import themes as th


class _StubOpenAI:
    """Stub that returns predictable themes based on input list size."""

    def __init__(self):
        self.last_messages = None

    class chat:  # type: ignore
        class completions:  # type: ignore
            @staticmethod
            def create(*args, **kwargs):  # type: ignore[override]
                stub: _StubOpenAI = _StubOpenAI._instance  # type: ignore[attr-defined]
                if args:
                    kwargs["messages"] = args[0]
                stub.last_messages = kwargs["messages"]
                # Respond with deterministic JSON array
                feedback_count = len(
                    [m for m in stub.last_messages if m["role"] == "user"]
                )
                if feedback_count == 0:  # pragma: no cover
                    array = []
                else:
                    array = ["theme1", "theme2", "theme3"]
                content = str(array).replace("'", '"')
                return {"choices": [{"message": {"content": content}}]}

    _instance: "_StubOpenAI" = None


@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    stub = _StubOpenAI()
    _StubOpenAI._instance = stub
    monkeypatch.setitem(sys.modules, "openai", stub)  # type: ignore[arg-type]
    yield stub
    sys.modules.pop("openai")


def test_extract_themes_basic(monkeypatch):
    feedback = [
        "Great teamwork and communication!",
        "We need more transparency on project goals.",
    ]
    themes: List[str] = th.extract_themes(feedback, max_themes=3)
    assert themes == ["theme1", "theme2", "theme3"]


def test_extract_themes_empty(monkeypatch):
    assert th.extract_themes([]) == []
