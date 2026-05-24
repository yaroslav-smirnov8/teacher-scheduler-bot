"""Lesson service - CRUD operations for single lessons"""
from datetime import datetime, date, time, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Lesson
import logging

logger = logging.getLogger(__name__)


class LessonService:
    """Lesson management service"""
    
    @staticmethod
    async def check_time_conflict(session: AsyncSession, teacher_id: int, student_id: int,
                           lesson_date: date, lesson_time: time,
                           exclude_lesson_id: Optional[int] = None) -> Tuple[bool, str]:
        """Check for time conflict"""
        query_teacher = select(Lesson).filter(
            Lesson.teacher_id == teacher_id,
            Lesson.date == lesson_date,
            Lesson.time == lesson_time
        )
        query_student = select(Lesson).filter(
            Lesson.student_id == student_id,
            Lesson.date == lesson_date,
            Lesson.time == lesson_time
        )

        if exclude_lesson_id:
            query_teacher = query_teacher.filter(Lesson.id != exclude_lesson_id)
            query_student = query_student.filter(Lesson.id != exclude_lesson_id)

        result_teacher = await session.execute(query_teacher)
        result_student = await session.execute(query_student)
        
        if result_teacher.scalar_one_or_none():
            return False, "The teacher already has a lesson scheduled at this time"
        if result_student.scalar_one_or_none():
            return False, "The student already has a lesson scheduled at this time"

        return True, ""
    
    @staticmethod
    async def create_lesson(session: AsyncSession, teacher_id: int, student_id: int,
                     lesson_date: date, lesson_time: time) -> Tuple[bool, str, Optional[Lesson]]:
        """Create lesson with validation"""
        if lesson_date < datetime.now(timezone.utc).date():
            return False, "Cannot schedule a lesson for a past date", None

        is_valid, error_msg = await LessonService.check_time_conflict(
            session, teacher_id, student_id, lesson_date, lesson_time
        )
        if not is_valid:
            return False, error_msg, None

        lesson = Lesson(
            date=lesson_date,
            time=lesson_time,
            teacher_id=teacher_id,
            student_id=student_id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)

        return True, "Lesson created successfully", lesson
    
    @staticmethod
    async def reschedule_lesson(session: AsyncSession, lesson_id: int, new_time: time) -> Tuple[bool, str]:
        """Reschedule lesson"""
        result = await session.execute(select(Lesson).filter_by(id=lesson_id))
        lesson = result.scalar_one_or_none()
        if not lesson:
            return False, "Lesson not found"

        if lesson.date < datetime.now(timezone.utc).date():
            return False, "Cannot reschedule a lesson in the past"

        is_valid, error_msg = await LessonService.check_time_conflict(
            session, lesson.teacher_id, lesson.student_id,
            lesson.date, new_time, exclude_lesson_id=lesson_id
        )
        if not is_valid:
            return False, error_msg

        lesson.time = new_time
        await session.commit()

        return True, "Lesson rescheduled successfully"
    
    @staticmethod
    async def cancel_lesson(session: AsyncSession, lesson_id: int) -> Tuple[bool, str, Optional[Lesson]]:
        """Cancel lesson"""
        result = await session.execute(select(Lesson).filter_by(id=lesson_id))
        lesson = result.scalar_one_or_none()
        if not lesson:
            return False, "Lesson not found", None

        lesson_copy = lesson
        await session.delete(lesson)
        await session.commit()

        return True, "Lesson cancelled", lesson_copy
    
    @staticmethod
    async def get_future_lessons(session: AsyncSession, student_id: int) -> List[Lesson]:
        """Get future lessons for a student"""
        today = datetime.now(timezone.utc).date()
        result = await session.execute(
            select(Lesson).filter(
                Lesson.student_id == student_id,
                Lesson.date >= today
            ).order_by(Lesson.date, Lesson.time)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_lessons_by_date(session: AsyncSession, teacher_id: int, lesson_date: date) -> List[Lesson]:
        """Get lessons for a teacher on a specific date"""
        result = await session.execute(
            select(Lesson).filter(
                Lesson.teacher_id == teacher_id,
                Lesson.date == lesson_date
            ).order_by(Lesson.time)
        )
        return result.scalars().all()
