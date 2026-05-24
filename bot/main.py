"""Entry point for the TeacherHelper aiogram bot"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import BOT_TOKEN
from database import init_db

# Middlewares
from bot.middlewares import DBSessionMiddleware, RateLimitMiddleware

# Filters
from bot.filters import IsTeacher, IsStudent

# Routers
from bot.routers.common import router as common_router
from bot.routers.teacher_registration import router as teacher_reg_router
from bot.routers.student_registration import router as student_reg_router
from bot.routers.add_student import router as add_student_router
from bot.routers.calendar import display_router, students_router, schedule_router
from bot.routers.recurring import create_router, convert_router, common_router as recurring_common_router
from bot.routers.reschedule import old_flow_router, student_flow_router, teacher_actions_router
from bot.routers.feedback import router as feedback_router
from bot.routers.homework import router as homework_router
from bot.routers.ai_homework import router as ai_homework_router
from bot.routers.payments import router as payments_router
# Unified background jobs
from bot.background_jobs import BackgroundJobs

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def homework_prompt_callback(lesson_id: int, teacher_id: int, student_id: int):
    """Callback when a lesson ends – prompt teacher to send homework"""
    from database import SessionLocal
    from models import Teacher, Student, Lesson
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    async with SessionLocal() as session:
        teacher = await session.get(Teacher, teacher_id)
        student = await session.get(Student, student_id)
        lesson = await session.get(Lesson, lesson_id)

        if teacher and teacher.telegram_id and student and lesson:
            try:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="📝 Send Homework Now",
                            callback_data=f"hw_post_lesson_{lesson_id}"
                        )]
                    ]
                )
                # Bot instance is passed via callback closure in background_jobs
                # This callback is called from BackgroundJobs which has bot access
                # We use a module-level bot reference set during init
                bot = _get_bot_instance()
                if bot:
                    await bot.send_message(
                        chat_id=teacher.telegram_id,
                        text=f"Lesson with {student.name} ended at {lesson.time.strftime('%H:%M')}. Send homework?",
                        reply_markup=keyboard,
                    )
                    logger.info(
                        f"Sent homework prompt to teacher {teacher_id} for lesson {lesson_id}"
                    )
            except Exception as e:
                logger.error(f"Error sending homework prompt: {e}")


_bot_instance: Bot | None = None


def _get_bot_instance() -> Bot | None:
    return _bot_instance


def _set_bot_instance(bot: Bot) -> None:
    global _bot_instance
    _bot_instance = bot


async def main():
    """Main entry point"""
    logger.info("Starting bot...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create bot and dispatcher
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    _set_bot_instance(bot)
    dp = Dispatcher()

    # Register middlewares
    dp.message.middleware(DBSessionMiddleware())
    dp.callback_query.middleware(DBSessionMiddleware())
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

    # Apply role-based filters to pure-role routers
    # Teacher-only routers
    add_student_router.message.filter(IsTeacher())
    add_student_router.callback_query.filter(IsTeacher())
    payments_router.message.filter(IsTeacher())
    payments_router.callback_query.filter(IsTeacher())
    create_router.message.filter(IsTeacher())
    create_router.callback_query.filter(IsTeacher())
    convert_router.message.filter(IsTeacher())
    convert_router.callback_query.filter(IsTeacher())
    teacher_actions_router.message.filter(IsTeacher())
    teacher_actions_router.callback_query.filter(IsTeacher())

    # Student-only routers
    old_flow_router.message.filter(IsStudent())
    old_flow_router.callback_query.filter(IsStudent())
    student_flow_router.message.filter(IsStudent())
    student_flow_router.callback_query.filter(IsStudent())

    # Register routers
    dp.include_router(common_router)
    dp.include_router(teacher_reg_router)
    dp.include_router(student_reg_router)
    dp.include_router(add_student_router)
    dp.include_router(display_router)
    dp.include_router(students_router)
    dp.include_router(schedule_router)
    dp.include_router(create_router)
    dp.include_router(convert_router)
    dp.include_router(recurring_common_router)
    dp.include_router(old_flow_router)
    dp.include_router(student_flow_router)
    dp.include_router(teacher_actions_router)
    dp.include_router(feedback_router)
    dp.include_router(homework_router)
    dp.include_router(ai_homework_router)
    dp.include_router(payments_router)

    # Start unified background jobs (single asyncio task)
    bg_jobs = BackgroundJobs(
        bot=bot,
        homework_prompt_callback=homework_prompt_callback,
        poll_interval=60,
        cleanup_interval=86400,
        retention_days=30,
    )
    bg_jobs.start()
    logger.info("Background jobs started")

    # Start polling
    logger.info("Bot started successfully")
    try:
        await dp.start_polling(bot)
    finally:
        # Cleanup
        await bg_jobs.stop()
        logger.info("Bot stopped")


if __name__ == '__main__':
    asyncio.run(main())
