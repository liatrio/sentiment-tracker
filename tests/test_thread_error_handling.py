"""Tests for thread error handling utilities in app module."""
from __future__ import annotations

import importlib
from unittest import mock

import src.app as app_module


def _boom() -> None:  # noqa: WPS110 – test helper
    raise RuntimeError("boom")


def test_submit_background_logs_exception():
    # Reload to ensure fresh logger references if other tests changed handlers.
    importlib.reload(app_module)

    with mock.patch.object(app_module.logger, "exception") as mock_exc:
        fut = app_module.submit_background(_boom)
        fut.exception(timeout=1)  # wait for completion without raising
        mock_exc.assert_called_once()
        # Ensure the exception message contains 'boom'
        args, _ = mock_exc.call_args
        assert "boom" in str(args[1])  # second positional arg is exception instance
