"""Unified background job runner — single asyncio task for all periodic jobs.
Delegates individual jobs to bot.jobs.* modules for better modularity.
"""
import asyncio
import logging
import time
from datetime import datetime, date, timezone
from typing import Optional, Callable, Awaitable

from aiogram import Bot

from bot.jobs import (
    check_ended_lessons,
    send_lesson_reminders,
    send_daily_summary,
    send_payment_reminders,
    cleanup_homework,
    cleanup_rate_limits,
    materialize_recurring_lessons,
)

logger = logging.getLogger(__name__)


class BackgroundJobs:
    """Single asyncio task running all periodic background jobs."""

    def __init__(
        self,
        bot: Bot,
        homework_prompt_callback: Optional[Callable[..., Awaitable[None]]] = None,
        poll_interval: int = 60,
        cleanup_interval: int = 86400,
        retention_days: int = 30,
    ):
        self.bot = bot
        self.homework_prompt_callback = homework_prompt_callback
        self.poll_interval = poll_interval
        self.cleanup_interval = cleanup_interval
        self.retention_days = retention_days
        self.running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the background loop."""
        if self.running:
            logger.warning("Background jobs already running")
            return
        self.running = True
        logger.info(
            f"Starting background jobs "
            f"(poll: {self.poll_interval}s, cleanup: {self.cleanup_interval}s, "
            f"retention: {self.retention_days}d)"
        )
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop the background loop gracefully."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background jobs stopped")

    async def _loop(self) -> None:
        """Main loop — checks timers and runs jobs as needed."""
        last_poll = 0.0
        last_reminders = 0.0
        last_summary_date: Optional[date] = None
        last_cleanup = 0.0
        last_rate_cleanup = 0.0

        while self.running:
            now = time.time()
            now_dt = datetime.now(timezone.utc)

            # Homework polling
            if now - last_poll >= self.poll_interval:
                await check_ended_lessons(self.homework_prompt_callback)
                last_poll = now

            # Lesson reminders (every hour)
            if now - last_reminders >= 3600:
                await send_lesson_reminders(self.bot)
                await send_payment_reminders(self.bot)
                last_reminders = now

            # Daily teacher summary (at 9:00 UTC, once per day)
            if now_dt.hour == 9 and last_summary_date != now_dt.date():
                await send_daily_summary(self.bot)
                last_summary_date = now_dt.date()

            # Daily maintenance (cleanup + recurring materialization)
            if now - last_cleanup >= self.cleanup_interval:
                await cleanup_homework(self.retention_days)
                await materialize_recurring_lessons()
                last_cleanup = now

            # Rate limit store cleanup (every hour)
            if now - last_rate_cleanup >= 3600:
                cleanup_rate_limits()
                last_rate_cleanup = now

            await asyncio.sleep(10)
