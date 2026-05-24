"""Payment service — lesson-level payment operations"""
import html
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Lesson, Student, PaymentTransaction

logger = logging.getLogger(__name__)


def _sanitize_note(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\0', '')
    text = html.escape(text)
    return text.strip()


class _LessonOpsMixin:
    """Mixin with per-lesson payment operations."""

    @staticmethod
    async def mark_lesson_paid(
        session: AsyncSession,
        lesson_id: int,
        admin_id: int,
        note: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Lesson]]:
        try:
            result = await session.execute(select(Lesson).filter_by(id=lesson_id))
            lesson = result.scalar_one_or_none()
            if not lesson:
                return False, "Lesson not found", None
            lesson.is_paid = True
            lesson.paid_at = datetime.now(timezone.utc)
            lesson.paid_by_admin_id = admin_id
            if note:
                lesson.payment_note = _sanitize_note(note)
            await session.commit()
            await session.refresh(lesson)
            logger.info(f"Lesson {lesson_id} marked as paid by admin {admin_id}")
            return True, "Lesson marked as paid", lesson
        except Exception as e:
            logger.error("Error marking lesson as paid: %s", e)
            await session.rollback()
            return False, "Payment error", None

    @staticmethod
    async def mark_lesson_unpaid(
        session: AsyncSession,
        lesson_id: int
    ) -> Tuple[bool, str, Optional[Lesson]]:
        try:
            result = await session.execute(select(Lesson).filter_by(id=lesson_id))
            lesson = result.scalar_one_or_none()
            if not lesson:
                return False, "Lesson not found", None
            lesson.is_paid = False
            lesson.paid_at = None
            lesson.paid_by_admin_id = None
            lesson.payment_note = None
            await session.commit()
            await session.refresh(lesson)
            logger.info(f"Lesson {lesson_id} marked as unpaid")
            return True, "Lesson marked as unpaid", lesson
        except Exception as e:
            logger.error("Error marking lesson as unpaid: %s", e)
            await session.rollback()
            return False, "Payment error", None

    @staticmethod
    async def get_unpaid_lessons(
        session: AsyncSession,
        teacher_id: int,
        days_back: int = 14,
        days_forward: int = 14
    ) -> List[Lesson]:
        try:
            today = date.today()
            start_date = today - timedelta(days=days_back)
            end_date = today + timedelta(days=days_forward)
            result = await session.execute(
                select(Lesson)
                .options(selectinload(Lesson.student))
                .filter(and_(
                    Lesson.teacher_id == teacher_id,
                    Lesson.date >= start_date,
                    Lesson.date <= end_date,
                    Lesson.is_paid.is_(False)
                ))
                .order_by(Lesson.date, Lesson.time)
            )
            lessons = result.scalars().all()
            logger.info(f"Found {len(lessons)} unpaid lessons for teacher {teacher_id}")
            return lessons
        except Exception as e:
            logger.error(f"Error getting unpaid lessons: {e}")
            return []

    @staticmethod
    async def get_upcoming_lessons(
        session: AsyncSession,
        teacher_id: int,
        days: int = 14
    ) -> List[Lesson]:
        try:
            today = date.today()
            end_date = today + timedelta(days=days)
            result = await session.execute(
                select(Lesson)
                .options(selectinload(Lesson.student))
                .filter(and_(
                    Lesson.teacher_id == teacher_id,
                    Lesson.date >= today,
                    Lesson.date <= end_date
                ))
                .order_by(Lesson.date, Lesson.time)
            )
            lessons = result.scalars().all()
            logger.info(f"Found {len(lessons)} upcoming lessons for teacher {teacher_id}")
            return lessons
        except Exception as e:
            logger.error(f"Error getting upcoming lessons: {e}")
            return []

    @staticmethod
    async def get_recent_lessons(
        session: AsyncSession,
        teacher_id: int,
        days: int = 14
    ) -> List[Lesson]:
        try:
            today = date.today()
            start_date = today - timedelta(days=days)
            result = await session.execute(
                select(Lesson)
                .options(selectinload(Lesson.student))
                .filter(and_(
                    Lesson.teacher_id == teacher_id,
                    Lesson.date >= start_date,
                    Lesson.date < today
                ))
                .order_by(Lesson.date.desc(), Lesson.time.desc())
            )
            lessons = result.scalars().all()
            logger.info(f"Found {len(lessons)} recent lessons for teacher {teacher_id}")
            return lessons
        except Exception as e:
            logger.error(f"Error getting recent lessons: {e}")
            return []

    @staticmethod
    async def get_lesson_payment_status(
        session: AsyncSession,
        lesson_id: int
    ) -> Optional[Lesson]:
        try:
            result = await session.execute(
                select(Lesson)
                .options(selectinload(Lesson.student), selectinload(Lesson.teacher))
                .filter_by(id=lesson_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting lesson payment status: {e}")
            return None

    @staticmethod
    async def update_payment_note(
        session: AsyncSession,
        lesson_id: int,
        note: str
    ) -> Tuple[bool, str]:
        try:
            result = await session.execute(select(Lesson).filter_by(id=lesson_id))
            lesson = result.scalar_one_or_none()
            if not lesson:
                return False, "Lesson not found"
            lesson.payment_note = _sanitize_note(note)
            await session.commit()
            logger.info(f"Updated payment note for lesson {lesson_id}")
            return True, "Payment note updated"
        except Exception as e:
            logger.error("Error updating payment note: %s", e)
            await session.rollback()
            return False, "Payment error"

    @staticmethod
    async def toggle_payment_reminders(
        session: AsyncSession,
        student_id: int,
        enabled: bool
    ) -> Tuple[bool, str]:
        try:
            result = await session.execute(select(Student).filter_by(id=student_id))
            student = result.scalar_one_or_none()
            if not student:
                return False, "Student not found"
            student.payment_reminders_enabled = enabled
            await session.commit()
            logger.info(f"Payment reminders {'enabled' if enabled else 'disabled'} for student {student_id}")
            return True, f"Payment reminders {'enabled' if enabled else 'disabled'}"
        except Exception as e:
            logger.error("Error toggling payment reminders: %s", e)
            await session.rollback()
            return False, "Payment error"

    @staticmethod
    async def get_lessons_needing_payment_reminder(
        session: AsyncSession,
        hours_before: int = 24,
        hours_after: int = 24
    ) -> List[Lesson]:
        try:
            now = datetime.now(timezone.utc)
            before_time = now + timedelta(hours=hours_before)
            after_time = now - timedelta(hours=hours_after)
            result = await session.execute(
                select(Lesson)
                .options(selectinload(Lesson.student), selectinload(Lesson.teacher))
                .filter(and_(
                    Lesson.is_paid.is_(False),
                    Lesson.payment_reminder_sent_at.is_(None),
                    or_(
                        and_(
                            Lesson.date == before_time.date(),
                            Lesson.time >= before_time.time()
                        ),
                        and_(
                            Lesson.date == after_time.date(),
                            Lesson.time <= after_time.time()
                        )
                    )
                ))
            )
            lessons = result.scalars().all()
            logger.info(f"Found {len(lessons)} lessons needing payment reminders")
            return lessons
        except Exception as e:
            logger.error(f"Error getting lessons needing payment reminders: {e}")
            return []

    @staticmethod
    async def mark_payment_reminder_sent(
        session: AsyncSession,
        lesson_id: int
    ) -> bool:
        try:
            result = await session.execute(select(Lesson).filter_by(id=lesson_id))
            lesson = result.scalar_one_or_none()
            if not lesson:
                return False
            lesson.payment_reminder_sent_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(f"Marked payment reminder sent for lesson {lesson_id}")
            return True
        except Exception as e:
            logger.error(f"Error marking payment reminder sent: {e}")
            await session.rollback()
            return False
