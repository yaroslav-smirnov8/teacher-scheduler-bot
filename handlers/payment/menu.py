"""Payment menu and lesson list handlers"""
import logging
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models import Teacher
from payment_service import PaymentService

logger = logging.getLogger(__name__)


async def payment_menu(query: CallbackQuery, state: FSMContext, session) -> None:
    """Main payment menu with filter options"""
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    keyboard = [
        [InlineKeyboardButton(text="\U0001f534 Unpaid lessons", callback_data="pay_unpaid")],
        [InlineKeyboardButton(text="\U0001f4c5 Upcoming lessons", callback_data="pay_upcoming")],
        [InlineKeyboardButton(text="\U0001f5d3 Recent lessons", callback_data="pay_recent")],
        [InlineKeyboardButton(text="\U0001f4b0 Deposit", callback_data="bulk_start")],
        [InlineKeyboardButton(text="\U0001f4b0 Balance History", callback_data="bal_menu")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")],
    ]

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await query.message.edit_text(
        text="\U0001f4b3 Payment Management\n\nSelect an option:",
        reply_markup=reply_markup
    )


async def payment_show_unpaid(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show unpaid lessons (past 14 days + future 14 days)"""
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    lessons = await PaymentService.get_unpaid_lessons(session, teacher.id)

    if not lessons:
        keyboard = [
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text(
            text="\U0001f534 Unpaid Lessons\n\nNo unpaid lessons found in the past 14 days and next 14 days.",
            reply_markup=reply_markup
        )
        return

    keyboard = []
    for lesson in lessons:
        student_name = lesson.student.name if lesson.student else "Unknown"
        date_str = lesson.date.strftime("%d %b")
        time_str = lesson.time.strftime("%H:%M")
        label = f"\U0001f534 {date_str} {time_str} \u2014 {student_name}"
        callback = f"pay_lesson:{lesson.id}:unpaid"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=callback)])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")])
    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await query.message.edit_text(
        text=f"\U0001f534 Unpaid Lessons\n\nFound {len(lessons)} unpaid lesson(s):",
        reply_markup=reply_markup
    )


async def payment_show_upcoming(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show upcoming lessons (next 14 days)"""
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    lessons = await PaymentService.get_upcoming_lessons(session, teacher.id)

    if not lessons:
        keyboard = [
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text(
            text="\U0001f4c5 Upcoming Lessons\n\nNo upcoming lessons in the next 14 days.",
            reply_markup=reply_markup
        )
        return

    keyboard = []
    for lesson in lessons:
        student_name = lesson.student.name if lesson.student else "Unknown"
        date_str = lesson.date.strftime("%d %b")
        time_str = lesson.time.strftime("%H:%M")
        status_icon = "\U0001f7e2" if lesson.is_paid else "\U0001f534"
        label = f"{status_icon} {date_str} {time_str} \u2014 {student_name}"
        callback = f"pay_lesson:{lesson.id}:upcoming"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=callback)])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")])
    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await query.message.edit_text(
        text=f"\U0001f4c5 Upcoming Lessons\n\nFound {len(lessons)} lesson(s):",
        reply_markup=reply_markup
    )


async def payment_show_recent(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show recent lessons (past 14 days)"""
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    lessons = await PaymentService.get_recent_lessons(session, teacher.id)

    if not lessons:
        keyboard = [
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text(
            text="\U0001f5d3 Recent Lessons\n\nNo lessons in the past 14 days.",
            reply_markup=reply_markup
        )
        return

    keyboard = []
    for lesson in lessons:
        student_name = lesson.student.name if lesson.student else "Unknown"
        date_str = lesson.date.strftime("%d %b")
        time_str = lesson.time.strftime("%H:%M")
        status_icon = "\U0001f7e2" if lesson.is_paid else "\U0001f534"
        label = f"{status_icon} {date_str} {time_str} \u2014 {student_name}"
        callback = f"pay_lesson:{lesson.id}:recent"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=callback)])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")])
    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await query.message.edit_text(
        text=f"\U0001f5d3 Recent Lessons\n\nFound {len(lessons)} lesson(s):",
        reply_markup=reply_markup
    )
