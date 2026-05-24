"""Payment lesson actions - details, mark paid/unpaid, send reminder"""
import logging
from datetime import datetime, timezone
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models import Teacher, Student
from payment_service import PaymentService
from access_control import AccessControlService
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)


async def payment_show_lesson_details(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show lesson payment details"""
    try:
        logger.info(f"payment_show_lesson_details called with callback_data: {query.data}")

        parts = query.data.split(":")
        if len(parts) < 3:
            await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
            return
        lesson_id = safe_parse_callback_int(query.data, delimiter=':', position=-2)
        if lesson_id is None:
            await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
            return
        source = parts[-1] if len(parts) >= 3 else None
        user_id = query.from_user.id

        result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
        teacher = result.scalar_one_or_none()

        if not teacher:
            await query.message.edit_text("You are not registered as a teacher.")
            return

        lesson = await PaymentService.get_lesson_payment_status(session, lesson_id)

        if not lesson:
            await query.message.edit_text("Lesson not found.")
            return

        if lesson.teacher_id != teacher.id:
            await query.message.edit_text("You can only view payment status for your own lessons.")
            return

        student_name = lesson.student.name if lesson.student else "Unknown"
        date_str = lesson.date.strftime("%d %B %Y")
        time_str = lesson.time.strftime("%H:%M")

        status_text = "\U0001f7e2 Paid" if lesson.is_paid else "\U0001f534 Unpaid"
        paid_at_text = ""
        if lesson.paid_at:
            paid_at_text = f"\nPaid at: {lesson.paid_at.strftime('%d.%m.%Y %H:%M')}"

        note_text = ""
        if lesson.payment_note:
            note_text = f"\nNote: {lesson.payment_note}"

        balance_text = ""
        if lesson.paid_from_balance and lesson.student:
            balance_text = f"\nPaid from balance ({lesson.student.paid_lessons_balance} remaining)"

        message = (
            f"\U0001f4b3 Payment Details\n\n"
            f"Student: {student_name}\n"
            f"Date: {date_str}\n"
            f"Time: {time_str}\n"
            f"Status: {status_text}{paid_at_text}{note_text}{balance_text}"
        )

        keyboard = []
        if lesson.is_paid:
            keyboard.append([InlineKeyboardButton(text="\u21a9\ufe0f Mark as unpaid", callback_data=f"pay_mark_unpaid:{lesson.id}")])
        else:
            keyboard.append([InlineKeyboardButton(text="\u2705 Mark as paid", callback_data=f"pay_mark_paid:{lesson.id}")])

        if lesson.paid_from_balance:
            keyboard.append([InlineKeyboardButton(text="\U0001f504 Return to Balance", callback_data=f"pay_refund:{lesson.id}")])
            keyboard.append([InlineKeyboardButton(text="\U0001f525 Forfeit Lesson", callback_data=f"pay_forfeit:{lesson.id}")])

        keyboard.append([InlineKeyboardButton(text="\u270f\ufe0f Edit note", callback_data=f"pay_edit_note:{lesson.id}")])
        keyboard.append([InlineKeyboardButton(text="\U0001f4e4 Send reminder", callback_data=f"pay_send_reminder:{lesson.id}")])
        if source == 'unpaid':
            keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Unpaid Lessons", callback_data="pay_unpaid")])
        elif source == 'upcoming':
            keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Upcoming Lessons", callback_data="pay_upcoming")])
        elif source == 'recent':
            keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Recent Lessons", callback_data="pay_recent")])
        keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")])
        keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await query.message.edit_text(
            text=message,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in payment_show_lesson_details: {e}", exc_info=True)
        try:
            await query.message.edit_text("\u26a0\ufe0f An error occurred. Please try again later.")
        except Exception:
            pass


def _build_lesson_detail_keyboard(lesson, source=None) -> InlineKeyboardMarkup:
    """Build keyboard for lesson detail view"""
    keyboard = []
    if lesson.is_paid:
        keyboard.append([InlineKeyboardButton(text="\u21a9\ufe0f Mark as unpaid", callback_data=f"pay_mark_unpaid:{lesson.id}")])
    else:
        keyboard.append([InlineKeyboardButton(text="\u2705 Mark as paid", callback_data=f"pay_mark_paid:{lesson.id}")])
    keyboard.append([InlineKeyboardButton(text="\u270f\ufe0f Edit note", callback_data=f"pay_edit_note:{lesson.id}")])
    keyboard.append([InlineKeyboardButton(text="\U0001f4e4 Send reminder", callback_data=f"pay_send_reminder:{lesson.id}")])
    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")])
    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _format_lesson_detail_message(lesson) -> str:
    """Format lesson detail message"""
    student_name = lesson.student.name if lesson.student else "Unknown"
    date_str = lesson.date.strftime("%d %B %Y")
    time_str = lesson.time.strftime("%H:%M")

    status_text = "\U0001f7e2 Paid" if lesson.is_paid else "\U0001f534 Unpaid"
    paid_at_text = f"\nPaid at: {lesson.paid_at.strftime('%d.%m.%Y %H:%M')}" if lesson.paid_at else ""
    note_text = f"\nNote: {lesson.payment_note}" if lesson.payment_note else ""

    return (
        f"\U0001f4b3 Payment Details\n\n"
        f"Student: {student_name}\n"
        f"Date: {date_str}\n"
        f"Time: {time_str}\n"
        f"Status: {status_text}{paid_at_text}{note_text}"
    )


async def payment_mark_paid(query: CallbackQuery, state: FSMContext, session) -> None:
    """Mark lesson as paid"""
    lesson_id = safe_parse_callback_int(query.data, delimiter=':', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    is_authorized, error_msg = await AccessControlService.verify_teacher_owns_lesson(
        session, teacher.id, lesson_id
    )
    if not is_authorized:
        await query.message.edit_text(error_msg)
        return

    success, message, lesson = await PaymentService.mark_lesson_paid(
        session, lesson_id, user_id, "Marked paid by admin"
    )

    if success:
        await query.answer("\u2705 Lesson marked as paid", show_alert=True)

        lesson = await PaymentService.get_lesson_payment_status(session, lesson_id)
        msg = _format_lesson_detail_message(lesson)
        reply_markup = _build_lesson_detail_keyboard(lesson)
        await query.message.edit_text(text=msg, reply_markup=reply_markup)
    else:
        await query.message.edit_text(f"Error: {message}")


async def payment_mark_unpaid(query: CallbackQuery, state: FSMContext, session) -> None:
    """Mark lesson as unpaid"""
    lesson_id = safe_parse_callback_int(query.data, delimiter=':', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    is_authorized, error_msg = await AccessControlService.verify_teacher_owns_lesson(
        session, teacher.id, lesson_id
    )
    if not is_authorized:
        await query.message.edit_text(error_msg)
        return

    success, message, lesson = await PaymentService.mark_lesson_unpaid(session, lesson_id)

    if success:
        await query.answer("\u21a9\ufe0f Lesson marked as unpaid", show_alert=True)

        lesson = await PaymentService.get_lesson_payment_status(session, lesson_id)
        msg = _format_lesson_detail_message(lesson)
        reply_markup = _build_lesson_detail_keyboard(lesson)
        await query.message.edit_text(text=msg, reply_markup=reply_markup)
    else:
        await query.message.edit_text(f"Error: {message}")


async def payment_send_reminder(query: CallbackQuery, state: FSMContext, session) -> None:
    """Send manual payment reminder to student"""
    lesson_id = safe_parse_callback_int(query.data, delimiter=':', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    lesson = await PaymentService.get_lesson_payment_status(session, lesson_id)

    if not lesson:
        await query.message.edit_text("Lesson not found.")
        return

    if lesson.teacher_id != teacher.id:
        await query.message.edit_text("You can only send reminders for your own lessons.")
        return

    if not lesson.student or not lesson.student.telegram_id:
        await query.message.edit_text("Student does not have a Telegram ID configured.")
        return

    try:
        date_str = lesson.date.strftime("%d.%m.%Y")
        time_str = lesson.time.strftime("%H:%M")

        if lesson.date >= datetime.now(timezone.utc).date():
            reminder_text = (
                f"Hi! Your lesson is scheduled for {date_str} at {time_str}. "
                f"Payment status is not marked as paid yet. "
                f"If you have already paid, please ignore this message \u2014 the teacher will update the status soon."
            )
        else:
            reminder_text = (
                f"Thank you for the lesson on {date_str} at {time_str}. "
                f"Payment status is not marked as paid yet. "
                f"If you have already paid, please ignore this message \u2014 the teacher will update the status soon."
            )

        await query.bot.send_message(
            chat_id=lesson.student.telegram_id,
            text=reminder_text
        )

        await PaymentService.mark_payment_reminder_sent(session, lesson_id)

        await query.answer("\u2705 Reminder sent to student", show_alert=True)

        lesson = await PaymentService.get_lesson_payment_status(session, lesson_id)
        msg = _format_lesson_detail_message(lesson)
        reply_markup = _build_lesson_detail_keyboard(lesson)
        await query.message.edit_text(text=msg, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error sending payment reminder: {e}")
        try:
            await query.message.edit_text("\u26a0\ufe0f Error sending reminder. Please try again later.")
        except Exception:
            pass


async def payment_refund_lesson(query: CallbackQuery, state: FSMContext, session) -> None:
    """Return a balance-paid lesson to balance."""
    lesson_id = safe_parse_callback_int(query.data, delimiter=':', position=-1)
    if lesson_id is None:
        await query.message.edit_text("\u26a0\ufe0f Invalid callback data.")
        return

    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    is_authorized, error_msg = await AccessControlService.verify_teacher_owns_lesson(
        session, teacher.id, lesson_id
    )
    if not is_authorized:
        await query.message.edit_text(error_msg)
        return

    success, message = await PaymentService.refund_lesson_to_balance(session, lesson_id)

    if success:
        await query.answer("\U0001f504 Lesson returned to balance", show_alert=True)
        lesson = await PaymentService.get_lesson_payment_status(session, lesson_id)
        msg = _format_lesson_detail_message(lesson)
        reply_markup = _build_lesson_detail_keyboard(lesson)
        await query.message.edit_text(text=msg, reply_markup=reply_markup)
    else:
        await query.message.edit_text(f"\u274c {message}")


async def payment_forfeit_lesson(query: CallbackQuery, state: FSMContext, session) -> None:
    """Forfeit a balance-paid lesson (no refund)."""
    lesson_id = safe_parse_callback_int(query.data, delimiter=':', position=-1)
    if lesson_id is None:
        await query.message.edit_text("\u26a0\ufe0f Invalid callback data.")
        return

    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    is_authorized, error_msg = await AccessControlService.verify_teacher_owns_lesson(
        session, teacher.id, lesson_id
    )
    if not is_authorized:
        await query.message.edit_text(error_msg)
        return

    success, message = await PaymentService.forfeit_lesson(session, lesson_id)

    if success:
        await query.answer("\U0001f525 Lesson forfeited", show_alert=True)
        lesson = await PaymentService.get_lesson_payment_status(session, lesson_id)
        msg = _format_lesson_detail_message(lesson)
        reply_markup = _build_lesson_detail_keyboard(lesson)
        await query.message.edit_text(text=msg, reply_markup=reply_markup)
    else:
        await query.message.edit_text(f"\u274c {message}")
