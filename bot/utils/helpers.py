"""Helper utilities for bot handlers"""
import json
import html
import re
import logging
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Teacher, Student

logger = logging.getLogger(__name__)


async def get_teacher(session: AsyncSession, telegram_id: int):
    """Get teacher by telegram_id"""
    result = await session.execute(select(Teacher).filter_by(telegram_id=telegram_id))
    return result.scalar_one_or_none()


async def get_student(session: AsyncSession, telegram_id: int):
    """Get student by telegram_id"""
    result = await session.execute(select(Student).filter_by(telegram_id=telegram_id))
    return result.scalar_one_or_none()


ACCEPTED_CANCEL_COMMANDS = {'cancel', 'exit', 'quit'}


def is_cancel_command(text: str) -> bool:
    """Check if user wants to cancel current operation"""
    return text.strip().lower() in ACCEPTED_CANCEL_COMMANDS


def sanitize_input(text):
    """Sanitize user input to prevent XSS and injection attacks."""
    if not text:
        return ""
    import html
    text = text.replace('\0', '')
    text = html.escape(text)
    text = text.strip()
    return text


def _sanitize_value(obj: Any) -> Any:
    """Recursively html.escape all string values in a nested dict/list structure."""
    if isinstance(obj, str):
        return html.escape(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_value(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_value(item) for item in obj]
    return obj


def sanitize_json_string(json_str: str) -> str:
    """Parse JSON, html.escape all string values, re-serialize.

    If parsing fails, return original string unchanged.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return json_str
    sanitized = _sanitize_value(data)
    return json.dumps(sanitized, indent=2, ensure_ascii=False)


def safe_parse_callback_int(data: str, delimiter: str = '-', position: int = -1) -> int | None:
    """Safely parse an integer from callback data.

    Args:
        data: The callback data string
        delimiter: The delimiter to split by (default: '-')
        position: Which element to extract (default: -1 for last)

    Returns:
        The parsed integer or None if parsing fails
    """
    try:
        parts = data.split(delimiter)
        return int(parts[position])
    except (ValueError, IndexError, TypeError):
        return None