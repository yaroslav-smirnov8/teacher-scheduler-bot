"""Daily summary job — sends morning schedule to all teachers."""
import logging
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import SessionLocal
from models import Teacher, Lesson

logger = logging.getLogger(__name__)


async def send_daily_summary(bot: Bot) -> None:
    """Send daily schedule summary to all teachers."""
    try:
        async with SessionLocal() as session:
            today = datetime.now(timezone.utc).date()
            result = await session.execute(select(Teacher))
            teachers = result.scalars().all()

            for teacher in teachers:
                if not teacher.telegram_id:
                    continue
                lessons_result = await session.execute(
                    select(Lesson).options(
                        selectinload(Lesson.student)
                    ).filter(
                        Lesson.teacher_id == teacher.id,
                        Lesson.date == today,
                    ).order_by(Lesson.time)
                )
                today_lessons = lessons_result.scalars().all()
                if today_lessons:
                    lessons_text = "\n".join([
                        f"• {l.time.strftime('%H:%M')} - "
                        f"{l.student.name if l.student else 'Unknown'}"
                        for l in today_lessons
                    ])
                    try:
                        await bot.send_message(
                            chat_id=teacher.telegram_id,
                            text=f"📚 Good morning! Your schedule for today:\n\n{lessons_text}",
                        )
                    except Exception as e:
                        logger.error(
                            f"Error sending daily summary to teacher {teacher.id}: {e}"
                        )
    except Exception as e:
        logger.error(f"Error in send_daily_summary: {e}")
