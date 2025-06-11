"""Sentiment analysis utilities using OpenAI.

This module provides a single public helper ``analyze_sentiment`` which calls
OpenAI ChatCompletion via the central ``openai_client`` wrapper and returns a
structured result.

The prompt asks the model to respond *only* with a compact JSON payload to make
machine-parsing deterministic.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from ..openai_client import chat_completion

_logger = logging.getLogger(__name__)


class SentimentLabel(str, Enum):
    """Enumeration of supported sentiment classes."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass(frozen=True)
class SentimentResult:
    """Structured sentiment analysis output."""

    label: SentimentLabel
    score: float  # range ‑1.0 .. 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {"label": self.label.value, "score": self.score}


_RESPONSE_RE = re.compile(r"\{[\s\S]*?\}")  # first JSON object in string


def _parse_response(content: str) -> SentimentResult:
    """Extract a ``SentimentResult`` from the model's raw string response."""

    match = _RESPONSE_RE.search(content)
    if not match:
        raise ValueError("Model response did not contain a JSON object")

    try:
        payload: Dict[str, Any] = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("Failed to parse JSON from model response") from exc

    label_raw = payload.get("label")
    score = payload.get("score")
    try:
        label = SentimentLabel(label_raw)
    except ValueError as exc:
        raise ValueError(f"Unexpected sentiment label: {label_raw}") from exc

    if not isinstance(score, (int, float)):
        raise ValueError("Score missing or not numeric")

    # clamp score for safety
    score_f = max(-1.0, min(1.0, float(score)))
    return SentimentResult(label=label, score=score_f)


_PROMPT_SYSTEM = (
    "You are a precise sentiment analysis assistant. "
    'Return ONLY a minified JSON like {"label":"positive", "score":0.8}.'
)


def analyze_sentiment(text: str, *, temperature: float = 0.0) -> SentimentResult:
    """Classify *text* as positive/neutral/negative using OpenAI.

    Parameters
    ----------
    text
        The text to classify.
    temperature
        Optional temperature forwarded to the model (default 0 for determinism).
    """

    messages = [
        {"role": "system", "content": _PROMPT_SYSTEM},
        {
            "role": "user",
            "content": (
                "Sentiment analysis request. Please identify sentiment label"
                " and a score between -1 and 1 (negative..positive).\n\nText:\n" + text
            ),
        },
    ]

    response = chat_completion(messages, temperature=temperature)
    try:
        content: str = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Model response missing expected fields") from exc

    return _parse_response(content)
