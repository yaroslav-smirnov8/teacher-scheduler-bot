"""User service - Working with teachers and students"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Teacher, Student


class UserService:
    """Service for working with users"""

    @staticmethod
    async def get_teacher_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[Teacher]:
        """Get teacher by telegram_id"""
        result = await session.execute(select(Teacher).filter_by(telegram_id=telegram_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_student_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[Student]:
        """Get student by telegram_id"""
        result = await session.execute(select(Student).filter_by(telegram_id=telegram_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_teacher_students(session: AsyncSession, teacher_id: int) -> List[Student]:
        """Get teacher's students"""
        result = await session.execute(select(Student).filter_by(teacher_id=teacher_id))
        return result.scalars().all()
