"""Notification service - Telegram notifications for lesson events"""
from datetime import date, time
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)


def _sanitize_text(text: str) -> str:
    """Sanitize text to prevent XSS when displayed with parse_mode=HTML."""
    if not text:
        return ""
    import html
    text = text.replace('\0', '')
    text = html.escape(text)
    return text.strip()


class NotificationService:
    """Service for sending notifications"""

    @staticmethod
    async def notify_student_lesson_created(bot, student, teacher,
                                            lesson_date: date, lesson_time: time) -> bool:
        """Notify student about lesson appointment"""
        if not student.telegram_id:
            return False

        try:
            await bot.send_message(
                chat_id=student.telegram_id,
                text=f"You have a lesson scheduled with {teacher.name} on {lesson_date} at {lesson_time.strftime('%H:%M')}."
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification to student {student.id}: {e}")
            return False

    @staticmethod
    async def notify_student_lesson_cancelled(bot, student, teacher,
                                              lesson_date: date, lesson_time: time,
                                              is_single_instance: bool = False) -> bool:
        """Notify student about lesson cancellation."""
        if not student.telegram_id:
            return False

        try:
            if is_single_instance:
                text = (f"The lesson with {teacher.name} on {lesson_date} at "
                        f"{lesson_time.strftime('%H:%M')} has been cancelled. "
                        f"This is a single cancellation - other lessons in the series remain scheduled.")
            else:
                text = f"The lesson with {teacher.name} on {lesson_date} at {lesson_time.strftime('%H:%M')} has been cancelled."
            await bot.send_message(
                chat_id=student.telegram_id,
                text=text
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification to student {student.id}: {e}")
            return False

    @staticmethod
    async def notify_student_recurring_created(bot, student, teacher, pattern) -> bool:
        """Notify student about creation of a recurring lesson series."""
        if not student.telegram_id:
            return False

        try:
            frequency_map = {
                'weekly': 'Every week',
                'biweekly': 'Every 2 weeks',
                'monthly': 'Every month'
            }
            freq_text = frequency_map.get(pattern.frequency, pattern.frequency)

            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            if pattern.frequency in ('weekly', 'biweekly') and pattern.weekday is not None:
                day_text = weekday_names[pattern.weekday]
                freq_text += f" on {day_text}"
            elif pattern.frequency == 'monthly' and pattern.day_of_month is not None:
                freq_text += f" on the {pattern.day_of_month}th"

            end_text = f" until {pattern.end_date}" if pattern.end_date else ""

            text = (f"A recurring lesson has been scheduled with {teacher.name}:\n"
                    f"{freq_text} at {pattern.time.strftime('%H:%M')}{end_text}")

            await bot.send_message(
                chat_id=student.telegram_id,
                text=text
            )
            return True
        except Exception as e:
            logger.error(f"Error sending recurring created notification to student {student.id}: {e}")
            return False

    @staticmethod
    async def notify_student_series_cancelled(bot, student, teacher, pattern) -> bool:
        """Notify student about cancellation of an entire recurring lesson series."""
        if not student.telegram_id:
            return False

        try:
            text = (f"All future recurring lessons with {teacher.name} have been cancelled. "
                    f"Past lessons in the series are preserved for history.")

            await bot.send_message(
                chat_id=student.telegram_id,
                text=text
            )
            return True
        except Exception as e:
            logger.error(f"Error sending series cancelled notification to student {student.id}: {e}")
            return False

    @staticmethod
    async def notify_student_reschedule_result(bot, student, teacher,
                                               lesson_date: date, new_time: time,
                                               accepted: bool) -> bool:
        """Notify student about reschedule result"""
        if not student.telegram_id:
            return False

        try:
            if accepted:
                text = f"Your lesson with {teacher.name} has been rescheduled to {lesson_date} at {new_time.strftime('%H:%M')}."
            else:
                text = f"Your request to reschedule the lesson with {teacher.name} was declined."

            await bot.send_message(chat_id=student.telegram_id, text=text)
            return True
        except Exception as e:
            logger.error(f"Error sending notification to student {student.id}: {e}")
            return False

    @staticmethod
    async def notify_teacher_reschedule_request(bot, teacher, student,
                                                lesson, new_hour: int, reason: str,
                                                keyboard) -> bool:
        """Notify teacher about reschedule request"""
        if not teacher.telegram_id:
            return False

        try:
            await bot.send_message(
                chat_id=teacher.telegram_id,
                text=f"Student {student.name} requests to reschedule the lesson from {lesson.time.strftime('%H:%M')} to {new_hour}:00 for reason: {_sanitize_text(reason)}. Do you agree?",
                reply_markup=keyboard
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification to teacher {teacher.id}: {e}")
            return False

    @staticmethod
    async def notify_teacher_reschedule_request_new(bot, teacher, student,
                                                    original_date: date, original_time: time,
                                                    requested_date: date, requested_time: time,
                                                    reason: str, keyboard) -> bool:
        """Notify teacher about reschedule request with clear OLD -> NEW visual."""
        if not teacher.telegram_id:
            return False

        try:
            text = (f"📅 Reschedule Request from {student.name}\n\n"
                    f"OLD: {original_date} {original_time.strftime('%H:%M')}\n"
                    f"NEW: {requested_date} {requested_time.strftime('%H:%M')}\n\n"
                    f"Reason: {_sanitize_text(reason)}\n\n"
                    f"Please approve or decline.")

            await bot.send_message(
                chat_id=teacher.telegram_id,
                text=text,
                reply_markup=keyboard
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification to teacher {teacher.id}: {e}")
            return False
