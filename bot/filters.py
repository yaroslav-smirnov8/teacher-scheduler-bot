"""Custom filters for aiogram handlers"""
from typing import Union
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from models import Teacher, Student
from database import SessionLocal


class IsTeacher(Filter):
    """Check if user is registered as teacher"""
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        if not event.from_user:
            return False
        async with SessionLocal() as session:
            result = await session.execute(select(Teacher).filter_by(telegram_id=event.from_user.id))
            return result.scalar_one_or_none() is not None


class IsStudent(Filter):
    """Check if user is registered as student"""
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        if not event.from_user:
            return False
        async with SessionLocal() as session:
            result = await session.execute(select(Student).filter_by(telegram_id=event.from_user.id))
            return result.scalar_one_or_none() is not None
