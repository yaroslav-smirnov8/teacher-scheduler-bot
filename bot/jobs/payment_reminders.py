"""Payment reminder job — sends reminders for unpaid lessons."""
import logging
from datetime import datetime, timezone

from aiogram import Bot

from database import SessionLocal
from payment_service import PaymentService

logger = logging.getLogger(__name__)


async def send_payment_reminders(bot: Bot) -> None:
    """Send payment reminders for unpaid lessons."""
    try:
        async with SessionLocal() as session:
            lessons = await PaymentService.get_lessons_needing_payment_reminder(session)
            for lesson in lessons:
                if (
                    lesson.student
                    and lesson.student.payment_reminders_enabled
                    and lesson.student.telegram_id
                ):
                    try:
                        date_str = lesson.date.strftime('%d.%m.%Y')
                        time_str = lesson.time.strftime('%H:%M')
                        if lesson.date >= datetime.now(timezone.utc).date():
                            text = (
                                f"Hi! Your lesson is scheduled for {date_str} at {time_str}. "
                                f"Payment status is not marked as paid yet. "
                                f"If you have already paid, please ignore this message."
                            )
                        else:
                            text = (
                                f"Thank you for the lesson on {date_str} at {time_str}. "
                                f"Payment status is not marked as paid yet. "
                                f"If you have already paid, please ignore this message."
                            )
                        await bot.send_message(
                            chat_id=lesson.student.telegram_id, text=text
                        )
                        await PaymentService.mark_payment_reminder_sent(
                            session, lesson.id
                        )
                    except Exception as e:
                        logger.error(f"Error sending payment reminder: {e}")
    except Exception as e:
        logger.error(f"Error in send_payment_reminders: {e}")
