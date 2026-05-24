"""Job to pre-create Lesson DB records from RecurringPattern entries."""
import logging
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import select

from database import SessionLocal
from models import Lesson, Student, RecurringPattern, RecurringException
from recurrence import RecurrenceGenerator
from services.payment.bulk_balance import apply_balance_to_lesson

logger = logging.getLogger(__name__)


async def materialize_recurring_lessons(lookahead_days: int = 60) -> int:
    """Pre-create Lesson DB records from RecurringPattern for the next N days.
    
    This ensures that recurring lesson instances are persisted so that
    homework_poll, lesson reminders, payment reminders, and the calendar
    month view can process them properly.
    
    Returns the number of lessons created.
    """
    try:
        async with SessionLocal() as session:
            today = datetime.now(timezone.utc).date()
            end_date = today + timedelta(days=lookahead_days)

            patterns_result = await session.execute(
                select(RecurringPattern).filter(
                    RecurringPattern.start_date <= end_date,
                    (RecurringPattern.end_date.is_(None)) | (RecurringPattern.end_date >= today),
                )
            )
            patterns = patterns_result.scalars().all()

            if not patterns:
                return 0

            created_count = 0
            for pattern in patterns:
                exception_result = await session.execute(
                    select(RecurringException).filter(
                        RecurringException.pattern_id == pattern.id,
                        RecurringException.exception_date.between(today, end_date),
                    )
                )
                exception_dates = {e.exception_date for e in exception_result.scalars().all()}

                existing_result = await session.execute(
                    select(Lesson.date).filter(
                        Lesson.recurring_pattern_id == pattern.id,
                        Lesson.date.between(today, end_date),
                    )
                )
                existing_dates = {row[0] for row in existing_result.fetchall()}

                new_lessons = []
                for occurrence_date in RecurrenceGenerator.generate_occurrences(
                    pattern, today, end_date, exception_dates
                ):
                    if occurrence_date not in existing_dates:
                        lesson = Lesson(
                            date=occurrence_date,
                            time=pattern.time,
                            teacher_id=pattern.teacher_id,
                            student_id=pattern.student_id,
                            recurring_pattern_id=pattern.id,
                        )
                        await apply_balance_to_lesson(session, lesson)
                        new_lessons.append(lesson)

                if new_lessons:
                    session.add_all(new_lessons)
                    created_count += len(new_lessons)
                    logger.info(
                        "Materialized %d lessons for recurring pattern %d (student %d)",
                        len(new_lessons), pattern.id, pattern.student_id,
                    )

            await session.commit()
            if created_count:
                logger.info(
                    "Recurring materialization: created %d lessons total "
                    "(lookahead: %d days)",
                    created_count, lookahead_days,
                )
            return created_count

    except Exception as e:
        logger.error("Error materializing recurring lessons: %s", e, exc_info=True)
        return 0
