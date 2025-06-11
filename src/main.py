"""Application bootstrap for Sentiment Tracker.

This module starts the Slack Bolt application via Socket Mode when executed
as a script. Keeping the runtime bootstrap here (instead of in ``src/app.py``)
ensures the core app module can be safely imported by unit tests and tooling
without side-effects.
"""
from __future__ import annotations

import os
import sys
from contextlib import suppress

from slack_bolt.adapter.socket_mode import SocketModeHandler

# Import the fully configured Bolt ``app`` and logger from the application
from src.app import app, logger, shutdown_executor


def main() -> None:  # pragma: no cover — manual run path
    """Start the Slack bot in Socket Mode.

    The function blocks until the process receives a termination signal
    (e.g., Ctrl-C). On shutdown it triggers graceful cleanup of background
    executors defined in ``src.app``.
    """

    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        logger.error(
            "Environment variable SLACK_APP_TOKEN is required to start the bot."
        )
        sys.exit(1)

    logger.info("Launching SocketModeHandler…")
    handler = SocketModeHandler(app, app_token)

    try:
        logger.info("Bot is ready to receive messages via Socket Mode.")
        handler.start()  # Blocking call
    except KeyboardInterrupt:  # pragma: no cover
        logger.info("Shutdown requested (KeyboardInterrupt). Exiting…")
    finally:
        # Ensure thread pool and scheduler shut down gracefully
        with suppress(Exception):
            shutdown_executor()
        logger.info("Goodbye.")


if __name__ == "__main__":  # pragma: no cover
    main()
