"""Payment service — bulk payment / refund / forfeit / balance history"""
import logging
from datetime import datetime, timezone
from typing import Tuple, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Student, Lesson, PaymentTransaction

logger = logging.getLogger(__name__)


async def apply_balance_to_lesson(session: AsyncSession, lesson: Lesson) -> bool:
    """If student has prepaid balance, mark lesson as paid from balance.
    Returns True if balance was applied, False otherwise."""
    student = await session.get(Student, lesson.student_id)
    if student and student.paid_lessons_balance > 0 and not lesson.is_paid:
        now = datetime.now(timezone.utc)
        balance_before = student.paid_lessons_balance
        student.paid_lessons_balance -= 1
        lesson.is_paid = True
        lesson.paid_from_balance = True
        lesson.paid_at = now
        txn = PaymentTransaction(
            student_id=student.id,
            teacher_id=lesson.teacher_id,
            type="apply",
            amount=-1,
            balance_before=balance_before,
            balance_after=student.paid_lessons_balance,
            lesson_id=lesson.id,
            created_at=now,
        )
        session.add(txn)
        return True
    return False


class _BalanceMixin:
    """Mixin with balance-based payment operations."""

    @staticmethod
    async def create_bulk_payment(
        session: AsyncSession,
        teacher_id: int,
        student_id: int,
        amount: int,
    ) -> Tuple[bool, str]:
        try:
            student = await session.execute(
                select(Student).filter_by(id=student_id).with_for_update()
            )
            student = student.scalar_one_or_none()
            if not student or student.teacher_id != teacher_id:
                return False, "Student not found"

            if amount < 1:
                return False, "Amount must be at least 1"

            now = datetime.now(timezone.utc)
            balance_before = student.paid_lessons_balance
            student.paid_lessons_balance += amount

            txn = PaymentTransaction(
                student_id=student_id,
                teacher_id=teacher_id,
                type="payment",
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_before + amount,
                note=f"Deposit of {amount} lesson(s)",
                created_at=now,
            )
            session.add(txn)

            applied_count = 0
            lessons_result = await session.execute(
                select(Lesson).filter(
                    Lesson.student_id == student_id,
                    Lesson.is_paid == False
                ).order_by(Lesson.date, Lesson.time)
            )
            for lesson in lessons_result.scalars().all():
                if student.paid_lessons_balance > 0:
                    if await apply_balance_to_lesson(session, lesson):
                        applied_count += 1

            await session.commit()
            logger.info(
                "Deposit: teacher=%d student=%d amount=%d (balance %d→%d, applied %d lesson(s))",
                teacher_id, student_id, amount, balance_before, balance_before + amount, applied_count,
            )
            return True, f"Deposited {amount} lessons, paid {applied_count} existing lesson(s)"

        except Exception as e:
            await session.rollback()
            logger.error("Error creating bulk payment: %s", e)
            return False, "Payment error"

    @staticmethod
    async def refund_lesson_to_balance(
        session: AsyncSession,
        lesson_id: int,
    ) -> Tuple[bool, str]:
        try:
            lesson = await session.get(Lesson, lesson_id)
            if not lesson or not lesson.paid_from_balance:
                return False, "Lesson was not paid from balance"

            student = await session.execute(
                select(Student).filter_by(id=lesson.student_id).with_for_update()
            )
            student = student.scalar_one_or_none()
            if not student:
                return False, "Student not found"

            balance_before = student.paid_lessons_balance
            lesson.is_paid = False
            lesson.paid_from_balance = False
            lesson.paid_at = None
            lesson.paid_by_admin_id = None
            lesson.payment_note = "Returned to balance"

            student.paid_lessons_balance += 1

            txn = PaymentTransaction(
                student_id=lesson.student_id,
                teacher_id=lesson.teacher_id,
                type="refund",
                amount=1,
                balance_before=balance_before,
                balance_after=balance_before + 1,
                lesson_id=lesson.id,
                note="Refunded from cancelled lesson",
                created_at=datetime.now(timezone.utc),
            )
            session.add(txn)
            await session.commit()

            logger.info("Refunded lesson %d to balance (student %d)", lesson_id, lesson.student_id)
            return True, "Lesson returned to balance"

        except Exception as e:
            await session.rollback()
            logger.error("Error refunding lesson to balance: %s", e)
            return False, "Payment error"

    @staticmethod
    async def forfeit_lesson(
        session: AsyncSession,
        lesson_id: int,
    ) -> Tuple[bool, str]:
        try:
            lesson = await session.get(Lesson, lesson_id)
            if not lesson or not lesson.paid_from_balance:
                return False, "Lesson was not paid from balance"

            if not lesson.is_paid:
                return False, "Lesson is not paid"

            student = await session.execute(
                select(Student).filter_by(id=lesson.student_id).with_for_update()
            )
            student = student.scalar_one_or_none()
            if not student:
                return False, "Student not found"

            balance_before = student.paid_lessons_balance
            lesson.paid_from_balance = False
            lesson.payment_note = "Forfeited (no-show / late cancel)"

            txn = PaymentTransaction(
                student_id=lesson.student_id,
                teacher_id=lesson.teacher_id,
                type="forfeit",
                amount=0,
                balance_before=balance_before,
                balance_after=balance_before,
                lesson_id=lesson.id,
                note="Forfeited — no refund",
                created_at=datetime.now(timezone.utc),
            )
            session.add(txn)
            await session.commit()

            logger.info("Forfeited lesson %d (student %d)", lesson_id, lesson.student_id)
            return True, "Lesson forfeited (payment not returned)"

        except Exception as e:
            await session.rollback()
            logger.error("Error forfeiting lesson: %s", e)
            return False, "Payment error"

    @staticmethod
    async def get_balance_history(
        session: AsyncSession,
        student_id: int,
        limit: int = 20,
    ) -> List[PaymentTransaction]:
        result = await session.execute(
            select(PaymentTransaction)
            .filter(PaymentTransaction.student_id == student_id)
            .order_by(PaymentTransaction.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
