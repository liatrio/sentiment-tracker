"""Render feedback reports using Jinja2 templates."""
from __future__ import annotations

import datetime as _dt
import logging
import os
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.analysis.anonymize import anonymize_quotes
from src.analysis.themes import extract_themes
from src.reporting.aggregator import ProcessedFeedback

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(enabled_extensions=(".j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _emoji_bar(counts: dict[str, int], max_emoji: int = 20) -> str:  # pragma: no cover
    """Return a string bar of emojis based on *counts*.

    Positive → 😊, Neutral → 😐, Negative → 🙁.  Limit total length to *max_emoji*.
    """

    pos = counts.get("positive", 0)
    neu = counts.get("neutral", 0)
    neg = counts.get("negative", 0)
    total = pos + neu + neg or 1

    scale = max_emoji / total
    pos_e = "😊" * max(1 if pos else 0, round(pos * scale))
    neu_e = "😐" * max(1 if neu else 0, round(neu * scale))
    neg_e = "🙁" * max(1 if neg else 0, round(neg * scale))
    return pos_e + neu_e + neg_e


def _split_highlights(items: List[str], *, max_each: int = 5):
    """Return (well, improve) bullet lists extracted from structured items."""
    well: List[str] = []
    improve: List[str] = []

    for it in items:
        # naive parse of "well=..., improve=..." pattern
        if "well=" in it:
            _, after = it.split("well=", 1)
            txt = after.split(",", 1)[0].strip()
            well.append(f"• {txt}")
        if "improve=" in it:
            _, after = it.split("improve=", 1)
            txt = after.strip()
            improve.append(f"• {txt}")

    return well[:max_each], improve[:max_each]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_report(processed: ProcessedFeedback) -> str:
    """Render a Slack-friendly markdown report from ``ProcessedFeedback``."""

    # Anonymize comments – swallow exceptions to guarantee report generation
    try:
        anon_items = anonymize_quotes(processed.all_items)
    except Exception as exc:  # noqa: BLE001 – robustness
        logger.warning("Anonymization failed, using raw quotes: %s", exc)
        anon_items = processed.all_items

    # Themes
    try:
        themes = extract_themes(anon_items)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Theme extraction failed: %s", exc)
        themes = []

    bullets_well, bullets_improve = _split_highlights(anon_items)

    template = _env.get_template("report.md.j2")
    rendered: str = template.render(
        session_id=processed.session_id,
        date=_dt.datetime.utcnow().strftime("%Y-%m-%d"),
        sentiment_counts=processed.sentiment_counts,
        stats=processed.stats,
        emoji_bar=_emoji_bar(processed.sentiment_counts),
        themes=themes,
        bullets_well=bullets_well,
        bullets_improve=bullets_improve,
        all_items=anon_items,
        version=os.getenv("REPORT_VERSION", "0.1"),
    )
    return rendered


def post_report_to_slack(
    *, processed: ProcessedFeedback, client, channel: str
):  # pragma: no cover
    """Send report to Slack *channel* using *client* (WebClient)."""

    report_text = render_report(processed)

    if len(report_text) < 2800:
        client.chat_postMessage(channel=channel, text=report_text)
    else:
        # Upload as a file if too long
        client.files_upload(
            channels=channel,
            title=f"Feedback Report {processed.session_id}",
            content=report_text,
            filename=f"feedback_{processed.session_id}.md",
            filetype="markdown",
        )
