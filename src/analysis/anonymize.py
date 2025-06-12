"""OpenAI-based quote anonymization utility."""
from __future__ import annotations

import json
import logging
import re
from typing import List

from src.openai_client import chat_completion

# Module logger
logger = logging.getLogger(__name__)

# Capture first JSON array (themes logic reused)
_ARRAY_RE = re.compile(r"\[[^\]]*\]")

_PROMPT_SYSTEM = (
    "You are a privacy specialist. Your task is to rewrite user quotes so that "
    "no personal identifiers remain. Replace names, @mentions, emails, role or "
    "company names with neutral placeholders like ‘someone’, ‘colleague’, etc. "
    "Keep the meaning and sentiment. DO NOT add commentary. Return ONLY a "
    "JSON array of rewritten quotes in the same order as input."
)


def _parse(content: str) -> List[str]:
    match = _ARRAY_RE.search(content)
    if not match:
        raise ValueError("Model response lacked JSON array")
    arr = json.loads(match.group(0))
    if not isinstance(arr, list) or not all(isinstance(x, str) for x in arr):
        raise ValueError("Expected JSON array of strings")
    return arr


def anonymize_quotes(quotes: List[str], *, temperature: float = 0.3) -> List[str]:
    """Rewrite *quotes* removing personal identifiers.

    If OpenAI fails, returns original quote prefixed with "[unredacted] ".
    """

    if not quotes:
        return []

    # Chunk up to 10 quotes per request.
    out: List[str] = []
    for i in range(0, len(quotes), 10):
        batch = quotes[i : i + 10]
        user_prompt = "Please anonymize the following quotes:\n" + "\n".join(batch)
        messages = [
            {"role": "system", "content": _PROMPT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
        try:
            resp = chat_completion(messages, temperature=temperature)
            rewritten = _parse(resp["choices"][0]["message"]["content"])
            if len(rewritten) != len(batch):
                raise ValueError("Length mismatch")
            out.extend(rewritten)
        except Exception as exc:  # noqa: BLE001
            # Log the root cause so we can debug why anonymization failed but continue gracefully.
            logger.warning(
                "Quote anonymization failed for batch: %s", exc, exc_info=True
            )
            out.extend([f"[unredacted] {q}" for q in batch])
    return out
