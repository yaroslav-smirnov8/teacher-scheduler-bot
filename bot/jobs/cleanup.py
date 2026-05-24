"""Cleanup jobs — homework cleanup and rate limit store cleanup."""
import logging

from database import SessionLocal
from homework_service import HomeworkService

logger = logging.getLogger(__name__)


async def cleanup_homework(retention_days: int = 30) -> None:
    """Delete old homework records."""
    try:
        async with SessionLocal() as session:
            deleted = await HomeworkService.cleanup_old_homework(
                session, days=retention_days
            )
            await session.commit()
            logger.info(
                f"Cleanup completed: removed {deleted} old homework records "
                f"(retention: {retention_days}d)"
            )
    except Exception as e:
        logger.error(f"Error running cleanup: {e}", exc_info=True)
        await session.rollback()


def cleanup_rate_limits() -> None:
    """Clean up old rate limit entries to prevent memory leaks."""
    from bot.middlewares import cleanup_old_rate_limit_entries
    cleanup_old_rate_limit_entries()
