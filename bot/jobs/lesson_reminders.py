"""Lesson reminder job — sends 24h and 1h reminders to students."""
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import SessionLocal
from models import Lesson

logger = logging.getLogger(__name__)


async def send_lesson_reminders(bot: Bot) -> None:
    """Send 24h and 1h lesson reminders to students."""
    try:
        async with SessionLocal() as session:
            now = datetime.now(timezone.utc)

            # 24h reminder
            tomorrow = now + timedelta(hours=24)
            tomorrow_start = tomorrow.replace(minute=0, second=0, microsecond=0)
            tomorrow_end = tomorrow_start + timedelta(hours=1)

            result_24h = await session.execute(
                select(Lesson).options(
                    selectinload(Lesson.student),
                    selectinload(Lesson.teacher),
                ).filter(
                    Lesson.date == tomorrow_start.date(),
                    Lesson.time >= tomorrow_start.time(),
                    Lesson.time < tomorrow_end.time(),
                )
            )
            for lesson in result_24h.scalars().all():
                if lesson.student and lesson.student.telegram_id:
                    try:
                        payment_status = ""
                        if not lesson.is_paid:
                            payment_status = " Payment status: not marked as paid yet."
                        await bot.send_message(
                            chat_id=lesson.student.telegram_id,
                            text=(
                                f"📅 Reminder: You have a lesson with "
                                f"{lesson.teacher.name} tomorrow at "
                                f"{lesson.time.strftime('%H:%M')}.{payment_status}"
                            ),
                        )
                    except Exception as e:
                        logger.error(f"Error sending 24h reminder: {e}")

            # 1h reminder
            one_hour = now + timedelta(hours=1)
            one_hour_start = one_hour.replace(minute=0, second=0, microsecond=0)
            one_hour_end = one_hour_start + timedelta(hours=1)

            result_1h = await session.execute(
                select(Lesson).options(
                    selectinload(Lesson.student),
                    selectinload(Lesson.teacher),
                ).filter(
                    Lesson.date == one_hour_start.date(),
                    Lesson.time >= one_hour_start.time(),
                    Lesson.time < one_hour_end.time(),
                )
            )
            for lesson in result_1h.scalars().all():
                if lesson.student and lesson.student.telegram_id:
                    try:
                        await bot.send_message(
                            chat_id=lesson.student.telegram_id,
                            text=(
                                f"⏰ Reminder: Your lesson with "
                                f"{lesson.teacher.name} starts in 1 hour at "
                                f"{lesson.time.strftime('%H:%M')}!"
                            ),
                        )
                    except Exception as e:
                        logger.error(f"Error sending 1h reminder: {e}")
    except Exception as e:
        logger.error(f"Error in send_lesson_reminders: {e}")
