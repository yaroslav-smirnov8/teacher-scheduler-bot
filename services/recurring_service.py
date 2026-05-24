"""Recurring lesson service - Create, convert, delete recurring lesson patterns"""
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Set, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models import Teacher, Student, Lesson, RecurringPattern, RecurringException
from recurrence import RecurrenceGenerator
from services.lesson_service import LessonService
from services.payment.bulk_balance import apply_balance_to_lesson
import logging

logger = logging.getLogger(__name__)


class RecurringLessonService:
    """Service for managing recurring lessons.
    
    Provides methods for creating, converting, and deleting recurring lessons,
    as well as generating lesson instances for a given time window.
    
    Optimized for weak hardware:
    - Lazy generation of lesson instances (only requested time window)
    - Minimal DB queries (3 queries max per request)
    - Uses generators for memory efficiency
    """
    
    @staticmethod
    async def create_recurring_lesson(
        session: AsyncSession,
        teacher_id: int,
        student_id: int,
        pattern: RecurringPattern
    ) -> Tuple[bool, str, Optional[RecurringPattern]]:
        """Create a new recurring lesson with validation."""
        if pattern.start_date < datetime.now(timezone.utc).date():
            return False, "Cannot create recurring lesson with a start date in the past", None
        
        if pattern.end_date is not None and pattern.end_date <= pattern.start_date:
            return False, "End date must be after start date", None
        
        is_valid, error_msg = await LessonService.check_time_conflict(
            session, teacher_id, student_id, pattern.start_date, pattern.time
        )
        if not is_valid:
            return False, error_msg, None
        
        try:
            pattern.teacher_id = teacher_id
            pattern.student_id = student_id
            
            session.add(pattern)
            await session.flush()
            
            first_lesson = Lesson(
                date=pattern.start_date,
                time=pattern.time,
                teacher_id=teacher_id,
                student_id=student_id,
                recurring_pattern_id=pattern.id
            )
            session.add(first_lesson)
            await apply_balance_to_lesson(session, first_lesson)
            await session.commit()
            await session.refresh(pattern)
            
            return True, "Recurring lesson created successfully", pattern
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating recurring lesson: {e}")
            return False, "Error creating recurring lesson. Please try again.", None
    
    @staticmethod
    async def convert_to_recurring(
        session: AsyncSession,
        lesson_id: int,
        pattern_config: dict
    ) -> Tuple[bool, str, Optional[RecurringPattern]]:
        """Convert a single lesson to a recurring lesson."""
        result = await session.execute(select(Lesson).filter_by(id=lesson_id))
        lesson = result.scalar_one_or_none()
        
        if lesson is None:
            return False, "Lesson not found", None
        
        if lesson.recurring_pattern_id is not None:
            return False, "Lesson is already part of a recurring series", None
        
        try:
            frequency = pattern_config.get('frequency', 'weekly')
            interval = pattern_config.get('interval', 1)
            end_date = pattern_config.get('end_date')
            
            pattern = RecurringPattern(
                teacher_id=lesson.teacher_id,
                student_id=lesson.student_id,
                start_date=lesson.date,
                end_date=end_date,
                time=lesson.time,
                frequency=frequency,
                interval=interval,
                weekday=lesson.date.weekday() if frequency in ('weekly', 'biweekly') else None,
                day_of_month=lesson.date.day if frequency == 'monthly' else None,
                created_from_lesson_id=lesson_id
            )
            
            session.add(pattern)
            await session.flush()
            
            lesson.recurring_pattern_id = pattern.id
            await session.commit()
            await session.refresh(pattern)
            
            return True, "Lesson converted to recurring series", pattern
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error converting lesson to recurring: {e}")
            return False, "Error converting lesson to recurring. Please try again.", None
    
    @staticmethod
    async def delete_single_instance(
        session: AsyncSession,
        lesson_id: int,
        lesson_date: date
    ) -> Tuple[bool, str]:
        """Delete a single instance of a recurring lesson."""
        result = await session.execute(select(Lesson).filter_by(id=lesson_id))
        lesson = result.scalar_one_or_none()
        
        if lesson is None:
            return False, "Lesson not found"
        
        try:
            if lesson.recurring_pattern_id is not None:
                existing = await session.execute(
                    select(RecurringException).filter_by(
                        pattern_id=lesson.recurring_pattern_id,
                        exception_date=lesson_date
                    )
                )
                if existing.scalar_one_or_none() is None:
                    exception = RecurringException(
                        pattern_id=lesson.recurring_pattern_id,
                        exception_date=lesson_date,
                        reason="Deleted by teacher"
                    )
                    session.add(exception)
            
            await session.delete(lesson)
            await session.commit()
            
            return True, "Single lesson instance deleted"
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting single instance: {e}")
            return False, "Error deleting lesson. Please try again."
    
    @staticmethod
    async def delete_recurring_series(
        session: AsyncSession,
        pattern_id: int
    ) -> Tuple[bool, str]:
        """Delete an entire recurring lesson series."""
        result = await session.execute(select(RecurringPattern).filter_by(id=pattern_id))
        pattern = result.scalar_one_or_none()
        
        if pattern is None:
            return False, "Recurring pattern not found"
        
        try:
            today = datetime.now(timezone.utc).date()
            
            future_lessons = await session.execute(
                select(Lesson).filter(
                    Lesson.recurring_pattern_id == pattern_id,
                    Lesson.date >= today
                )
            )
            for lesson in future_lessons.scalars().all():
                await session.delete(lesson)
            
            await session.delete(pattern)
            await session.commit()
            
            return True, "Recurring series deleted"
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting recurring series: {e}")
            return False, "Error deleting recurring series. Please try again."
    
    @staticmethod
    async def get_recurring_lessons(
        session: AsyncSession,
        teacher_id: Optional[int] = None,
        student_id: Optional[int] = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Lesson]:
        """Get all lessons (recurring and one-time) for a given time window."""
        if start_date is None:
            start_date = datetime.now(timezone.utc).date()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        conditions = []
        if teacher_id is not None:
            conditions.append(RecurringPattern.teacher_id == teacher_id)
        if student_id is not None:
            conditions.append(RecurringPattern.student_id == student_id)
        
        if not conditions:
            return []
        
        patterns_result = await session.execute(
            select(RecurringPattern).options(selectinload(RecurringPattern.student)).filter(
                and_(
                    or_(*conditions),
                    RecurringPattern.start_date <= end_date,
                    or_(
                        RecurringPattern.end_date.is_(None),
                        RecurringPattern.end_date >= start_date
                    )
                )
            )
        )
        patterns = patterns_result.scalars().all()
        
        pattern_ids = [p.id for p in patterns]
        exception_map: dict[int, Set[date]] = {}
        
        if pattern_ids:
            exceptions_result = await session.execute(
                select(RecurringException).filter(
                    RecurringException.pattern_id.in_(pattern_ids),
                    RecurringException.exception_date.between(start_date, end_date)
                )
            )
            exceptions = exceptions_result.scalars().all()
            
            for exc in exceptions:
                if exc.pattern_id not in exception_map:
                    exception_map[exc.pattern_id] = set()
                exception_map[exc.pattern_id].add(exc.exception_date)
        
        lesson_lookup: dict[tuple[int, date], Lesson] = {}
        if pattern_ids:
            all_lessons_result = await session.execute(
                select(Lesson).options(selectinload(Lesson.student)).filter(
                    Lesson.recurring_pattern_id.in_(pattern_ids),
                    Lesson.date.between(start_date, end_date)
                )
            )
            for lesson in all_lessons_result.scalars().all():
                lesson_lookup[(lesson.recurring_pattern_id, lesson.date)] = lesson

        lessons: List[Lesson] = []
        for pattern in patterns:
            exception_dates = exception_map.get(pattern.id, set())
            
            for occurrence_date in RecurrenceGenerator.generate_occurrences(
                pattern, start_date, end_date, exception_dates
            ):
                existing_lesson = lesson_lookup.get((pattern.id, occurrence_date))
                
                if existing_lesson:
                    lessons.append(existing_lesson)
                else:
                    lesson = Lesson(
                        date=occurrence_date,
                        time=pattern.time,
                        teacher_id=pattern.teacher_id,
                        student_id=pattern.student_id,
                        recurring_pattern_id=pattern.id
                    )
                    lesson.student = pattern.student
                    lessons.append(lesson)
        
        one_time_conditions = []
        if teacher_id is not None:
            one_time_conditions.append(Lesson.teacher_id == teacher_id)
        if student_id is not None:
            one_time_conditions.append(Lesson.student_id == student_id)
        
        one_time_result = await session.execute(
            select(Lesson).options(selectinload(Lesson.student)).filter(
                and_(
                    or_(*one_time_conditions),
                    Lesson.date.between(start_date, end_date),
                    Lesson.recurring_pattern_id.is_(None)
                )
            )
        )
        one_time_lessons = one_time_result.scalars().all()
        lessons.extend(one_time_lessons)
        
        lessons.sort(key=lambda l: (l.date, l.time))
        
        return lessons
