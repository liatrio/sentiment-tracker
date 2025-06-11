"""Unit tests for the custom Scheduler class."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.scheduler import Scheduler


class TestScheduler:
    """Verify Scheduler executes callbacks and handles edge-cases."""

    def test_schedule_executes_callback_after_delay(self):
        """Callback should run after the specified delay using the executor."""
        executed = threading.Event()

        def _callback(arg: str) -> None:  # noqa: D401 – simple test function
            assert arg == "hello"
            executed.set()

        with ThreadPoolExecutor(max_workers=2) as executor:
            sched = Scheduler(executor)
            sched.schedule(0.05, _callback, "hello")  # 50 ms delay

            # Wait up to 0.5 s for callback to fire.
            assert executed.wait(0.5), "Scheduled callback did not execute in time"
            sched.shutdown()

    def test_schedule_negative_delay_raises(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            sched = Scheduler(executor)
            with pytest.raises(ValueError):
                sched.schedule(-1, lambda: None)
            sched.shutdown()

    def test_shutdown_stops_background_thread(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            sched = Scheduler(executor)
            # Scheduler thread should be alive initially
            assert sched._thread.is_alive()
            sched.shutdown()
            # After shutdown, thread should have terminated
            assert not sched._thread.is_alive()
