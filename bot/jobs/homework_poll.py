"""Homework polling job — detects ended lessons and triggers homework prompts."""
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

from sqlalchemy import select, and_, update

from database import SessionLocal
from models import Lesson, Student, PaymentTransaction

logger = logging.getLogger(__name__)


async def check_ended_lessons(
    homework_prompt_callback: Callable[..., Awaitable[None]],
) -> None:
    """Detect ended lessons and trigger homework prompts."""
    if not homework_prompt_callback:
        return
    async with SessionLocal() as session:
        try:
            now = datetime.now(timezone.utc)
            current_date = now.date()

            past_result = await session.execute(
                select(Lesson).where(
                    and_(
                        Lesson.date < current_date,
                        Lesson.homework_prompt_sent_at.is_(None),
                    )
                ).order_by(Lesson.date.desc(), Lesson.time.desc())
            )
            past_lessons = past_result.scalars().all()

            today_result = await session.execute(
                select(Lesson).where(
                    and_(
                        Lesson.date == current_date,
                        Lesson.time <= now.time(),
                        Lesson.homework_prompt_sent_at.is_(None),
                    )
                ).order_by(Lesson.time.desc())
            )
            today_lessons = today_result.scalars().all()

            prompted = 0
            for lesson in past_lessons + today_lessons:
                try:
                    stmt = (
                        update(Lesson)
                        .where(Lesson.id == lesson.id, Lesson.homework_prompt_sent_at.is_(None))
                        .values(homework_prompt_sent_at=now)
                    )
                    result = await session.execute(stmt)
                    if result.rowcount == 0:
                        continue

                    await homework_prompt_callback(
                        lesson_id=lesson.id,
                        teacher_id=lesson.teacher_id,
                        student_id=lesson.student_id,
                    )

                    student = await session.get(Student, lesson.student_id)
                    if student and student.paid_lessons_balance > 0 and not lesson.is_paid:
                        balance_before = student.paid_lessons_balance
                        student.paid_lessons_balance -= 1

                        lesson.is_paid = True
                        lesson.paid_at = now
                        lesson.paid_from_balance = True
                        lesson.payment_note = "Auto-paid from balance"

                        txn = PaymentTransaction(
                            student_id=lesson.student_id,
                            teacher_id=lesson.teacher_id,
                            type="apply",
                            amount=-1,
                            balance_before=balance_before,
                            balance_after=student.paid_lessons_balance,
                            lesson_id=lesson.id,
                            created_at=now,
                        )
                        session.add(txn)
                        logger.info(
                            "Auto-paid lesson %d from balance (student %d, balance %d→%d)",
                            lesson.id, lesson.student_id, balance_before,
                            student.paid_lessons_balance,
                        )

                    prompted += 1
                except Exception as e:
                    logger.error(f"Error processing lesson {lesson.id}: {e}")

            if prompted:
                logger.info("Lesson polling: Triggered %d homework prompts", prompted)

            await session.commit()
        except Exception as e:
            logger.error(f"Error checking ended lessons: {e}", exc_info=True)
            await session.rollback()
