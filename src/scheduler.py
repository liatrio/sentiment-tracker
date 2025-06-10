"""Lightweight task scheduler for non-blocking timed callbacks.

The Scheduler maintains a background daemon thread that sleeps until the
next task is due, then submits the task to a shared ThreadPoolExecutor.
This avoids spawning a new thread per timer (as `threading.Timer` does)
and keeps the main application thread unblocked.

The scheduler supports:
• schedule() – run a callable after a delay (seconds) and returns a task id.
• shutdown() – stop the scheduler gracefully, ensuring pending tasks are
  dispatched before exit.

Cancellation can be added later if required.
"""
from __future__ import annotations

import heapq
import itertools
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Tuple

logger = logging.getLogger(__name__)


class _ScheduledItem:
    """Internal container for a scheduled callback."""

    __slots__ = ("run_at", "task_id", "callback", "args", "kwargs")

    def __init__(
        self,
        run_at: float,
        task_id: int,
        callback: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        self.run_at = run_at
        self.task_id = task_id
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    # Heap ordering by run_at then task_id ensures stability.
    def __lt__(self, other: "_ScheduledItem") -> bool:  # type: ignore[override]
        return (self.run_at, self.task_id) < (other.run_at, other.task_id)


class Scheduler:
    """A minimal, thread-safe scheduler for delayed callbacks."""

    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self._executor = executor
        self._lock = threading.Condition()
        self._queue: list[_ScheduledItem] = []
        self._task_counter = itertools.count()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="scheduler")
        self._thread.start()
        logger.info("Scheduler started.")

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def schedule(
        self,
        delay_seconds: float,
        callback: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> int:
        """Schedule *callback* to be executed after *delay_seconds*.

        Returns a unique integer task id.
        """
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")
        run_at = time.time() + delay_seconds
        task_id = next(self._task_counter)
        item = _ScheduledItem(run_at, task_id, callback, args, kwargs)
        with self._lock:
            heapq.heappush(self._queue, item)
            self._lock.notify()
        return task_id

    def shutdown(self) -> None:
        """Stop the scheduler and wait for the background thread to finish."""
        with self._lock:
            self._running = False
            self._lock.notify()
        self._thread.join()
        logger.info("Scheduler shut down.")

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------
    def _run(self) -> None:  # noqa: D401 – simple private method
        """Background thread: dispatch tasks when due."""
        while True:
            with self._lock:
                # Wait until there is a task or we are stopping.
                while self._running and not self._queue:
                    self._lock.wait()
                if not self._running:
                    break
                # Peek at earliest task.
                next_item = self._queue[0]
                now = time.time()
                delay = next_item.run_at - now
                if delay > 0:
                    # Sleep until due or until new task arrives / shutdown.
                    self._lock.wait(timeout=delay)
                    continue
                # Task is due.
                heapq.heappop(self._queue)
            # Submit outside the lock to avoid deadlocks.
            try:
                self._executor.submit(next_item.callback, *next_item.args, **next_item.kwargs)  # type: ignore[name-defined]
            except Exception:  # pragma: no cover – log and keep going
                logger.exception(
                    "Error submitting scheduled task %s", next_item.task_id
                )
