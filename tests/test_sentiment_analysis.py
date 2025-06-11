"""Unit tests for analyze_sentiment utility."""
from typing import Dict

import pytest

from src.analysis import sentiment as sa


class _StubOpenAI:
    """Simple stub mimicking openai.ChatCompletion behavior."""

    def __init__(self):
        self.calls: Dict[str, Dict] = {}

    class ChatCompletion:
        @staticmethod
        def create(*args, **kwargs):  # type: ignore[override]
            if args:
                # First positional arg is expected to be messages list
                kwargs["messages"] = args[0]

            _StubOpenAI._instance.calls = kwargs  # type: ignore[attr-defined]
            prompt = kwargs["messages"][1]["content"]
            if "great" in prompt:
                label, score = "positive", 0.9
            elif "meh" in prompt:
                label, score = "neutral", 0.0
            else:
                label, score = "negative", -0.8
            content = f'{{"label": "{label}", "score": {score}}}'
            return {"choices": [{"message": {"content": content}}]}

    _instance: "_StubOpenAI" = None  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    stub = _StubOpenAI()
    _StubOpenAI._instance = stub
    monkeypatch.setattr(
        sa,
        "chat_completion",
        lambda *a, **k: _StubOpenAI.ChatCompletion.create(*a, **k),
    )
    yield


def test_positive():
    res = sa.analyze_sentiment("This product is great!")
    assert res.label == sa.SentimentLabel.POSITIVE
    assert res.score > 0.5


def test_neutral():
    res = sa.analyze_sentiment("It was meh.")
    assert res.label == sa.SentimentLabel.NEUTRAL


def test_negative():
    res = sa.analyze_sentiment("Terrible experience")
    assert res.label == sa.SentimentLabel.NEGATIVE
    assert res.score < 0


def test_bad_json():
    def bad_chat(*_, **__):
        return {"choices": [{"message": {"content": "no json here"}}]}

    sa.chat_completion = bad_chat  # type: ignore[assignment]
    with pytest.raises(ValueError):
        sa.analyze_sentiment("oops")
