"""Middlewares for aiogram bot: DB session injection and rate limiting"""
import logging
import time
from typing import Any, Dict, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database import SessionLocal

logger = logging.getLogger(__name__)

# Rate limiting storage: {telegram_id: [timestamp1, timestamp2, ...]}
_rate_limit_store: Dict[int, list] = {}
RATE_LIMIT_MAX_REQUESTS = 35
RATE_LIMIT_WINDOW_SECONDS = 60


class DBSessionMiddleware(BaseMiddleware):
    """Inject async database session into handler data"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with SessionLocal() as session:
            data['session'] = session
            return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting for all handlers"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Get user ID
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        current_time = time.time()

        # Clean old entries
        if user_id in _rate_limit_store:
            _rate_limit_store[user_id] = [
                ts for ts in _rate_limit_store[user_id]
                if current_time - ts < RATE_LIMIT_WINDOW_SECONDS
            ]
        else:
            _rate_limit_store[user_id] = []

        # Check limit
        if len(_rate_limit_store[user_id]) >= RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ You're sending too many requests. Please wait a moment before trying again."
                )
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(
                        "⚠️ Too many requests. Please wait.",
                        show_alert=True
                    )
                except Exception:
                    pass
            return None

        _rate_limit_store[user_id].append(current_time)
        return await handler(event, data)


def cleanup_old_rate_limit_entries():
    """Clean up old rate limit entries to prevent memory leaks"""
    current_time = time.time()
    cutoff_time = current_time - RATE_LIMIT_WINDOW_SECONDS * 2

    for user_id in list(_rate_limit_store.keys()):
        _rate_limit_store[user_id] = [
            ts for ts in _rate_limit_store[user_id]
            if ts > cutoff_time
        ]
        if not _rate_limit_store[user_id]:
            del _rate_limit_store[user_id]

    logger.debug("Cleaned up old rate limit entries")