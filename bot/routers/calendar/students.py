"""Student list and delete handlers"""
import logging
from datetime import datetime, date, timedelta, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Teacher, Student, Lesson, Homework, PaymentTransaction
from bot.utils.helpers import get_teacher, safe_parse_callback_int
from payment_service import PaymentService
from handlers.payment import BulkPaymentStates
from handlers.homework.teacher import _homework_teacher_icon
from homework_service import HomeworkService

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == 'list_students')
async def list_students_callback(query: CallbackQuery, session: AsyncSession):
    """Show list of students with delete buttons"""
    await query.answer()
    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    result = await session.execute(select(Student).filter_by(teacher_id=teacher.id))
    students = result.scalars().all()
    if not students:
        await query.message.edit_text("👥 You have no students.")
        return

    keyboard = []
    for student in students:
        contact = student.contact_info or 'No contact'
        keyboard.append([
            InlineKeyboardButton(text=f"{student.name} - {contact}", callback_data=f"student_info-{student.id}"),
            InlineKeyboardButton(text="\U0001f5d1\ufe0f Delete", callback_data=f"delete_student-{student.id}")
        ])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data='back_to_main')])
    await query.message.edit_text("👥 Your students:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


async def _render_student_card(query: CallbackQuery, session: AsyncSession, student: Student):
    """Render the student info card (shared between routes)"""
    today = datetime.now(timezone.utc).date()
    lessons_result = await session.execute(
        select(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time)
    )
    upcoming_lessons = lessons_result.scalars().all()

    unpaid_result = await session.execute(
        select(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.is_paid.is_(False),
            Lesson.date >= today - timedelta(days=14)
        ).order_by(Lesson.date, Lesson.time)
    )
    unpaid_lessons = unpaid_result.scalars().all()

    homework_result = await session.execute(
        select(Homework).filter(
            Homework.student_id == student.id,
            Homework.status != 'completed'
        ).order_by(Homework.sent_at.desc()).limit(5)
    )
    active_homework = homework_result.scalars().all()

    paid_lessons_result = await session.execute(
        select(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.is_paid == True
        )
    )
    paid_lessons_count = len(paid_lessons_result.scalars().all())

    telegram_status = "✅ Registered" if student.telegram_id else "❌ Not registered"
    contact = student.contact_info or "Not provided"

    lines = [
        f"<b>Student: {student.name}</b>\n",
        f"Telegram: {telegram_status}",
        f"Contact: {contact}",
        f"💰 Prepaid balance: {student.paid_lessons_balance} lesson(s)",
        f"✅ Paid lessons total: {paid_lessons_count}",
    ]

    if upcoming_lessons:
        lines.append(f"<b>Upcoming lessons ({len(upcoming_lessons)}):</b>")
        for lesson in upcoming_lessons[:5]:
            status = "✅ Paid" if lesson.is_paid else "🔴 Unpaid"
            recurring = " 🔁" if lesson.recurring_pattern_id else ""
            lines.append(f"  {lesson.date} {lesson.time.strftime('%H:%M')} — {status}{recurring}")
        if len(upcoming_lessons) > 5:
            lines.append(f"  ... and {len(upcoming_lessons) - 5} more")
    else:
        lines.append("📭 No upcoming lessons")

    if unpaid_lessons:
        lines.append(f"\n<b>Unpaid lessons ({len(unpaid_lessons)}):</b>")
        for lesson in unpaid_lessons[:3]:
            lines.append(f"  {lesson.date} {lesson.time.strftime('%H:%M')}")
        if len(unpaid_lessons) > 3:
            lines.append(f"  ... and {len(unpaid_lessons) - 3} more")

    hw_stats = await HomeworkService.get_homework_stats(session, student.teacher_id, student_id=student.id)
    if hw_stats['total'] > 0:
        lines.append(f"\n<b>Homework stats:</b>")
        lines.append(f"  \U0001f4e4 {hw_stats['sent_count']} sent, \U0001f4e5 {hw_stats['received_count']} received, \u2705 {hw_stats['completed']} completed")
        lines.append(f"  \U0001f4ca Completion: {hw_stats['completion_pct']}%")
    else:
        lines.append("\n\U0001f4cb No homework yet")

    if active_homework:
        lines.append(f"\n<b>Active homework ({len(active_homework)}):</b>")
        for hw in active_homework[:3]:
            icon = _homework_teacher_icon(hw)
            lines.append(f"  {icon} {hw.sent_at.strftime('%d.%m')} — {hw.text[:50]}...")
    else:
        lines.append("\n\U0001f4dd No active homework")

    keyboard = [
        [InlineKeyboardButton(text="📅 Open calendar", callback_data='calendar')],
        [InlineKeyboardButton(text="📝 Send homework", callback_data='teacher_homework_start')],
        [InlineKeyboardButton(text=f"📊 Hw stats", callback_data=f"hw_student_stats_{student.id}")],
        [InlineKeyboardButton(text=f"💰 Balance: {student.paid_lessons_balance}", callback_data=f"student_balance-{student.id}"),
         InlineKeyboardButton(text="💳 Deposit", callback_data=f"quick_deposit-{student.id}")],
        [InlineKeyboardButton(text="⬅️ Back to students", callback_data='list_students')],
        [InlineKeyboardButton(text="⬅️ Back to main", callback_data='back_to_main')],
    ]

    await query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@router.callback_query(F.data.startswith('student_info-'))
async def show_student_info(query: CallbackQuery, session: AsyncSession):
    """Show detailed student information"""
    await query.answer()
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    result = await session.execute(select(Student).filter_by(id=student_id))
    student = result.scalar_one_or_none()
    if not student or student.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only view your own students.")
        return

    await _render_student_card(query, session, student)


@router.callback_query(F.data.startswith('quick_deposit-'))
async def quick_deposit(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Quick deposit from student info card"""
    await query.answer()
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("Invalid callback data.")
        return

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    student = await session.get(Student, student_id)
    if not student or student.teacher_id != teacher.id:
        await query.message.edit_text("Access denied.")
        return

    keyboard = [
        [InlineKeyboardButton(text="2 lessons", callback_data="bulk_amt_2")],
        [InlineKeyboardButton(text="3 lessons", callback_data="bulk_amt_3")],
        [InlineKeyboardButton(text="4 lessons", callback_data="bulk_amt_4")],
        [InlineKeyboardButton(text="5 lessons", callback_data="bulk_amt_5")],
        [InlineKeyboardButton(text="6 lessons", callback_data="bulk_amt_6")],
        [InlineKeyboardButton(text="8 lessons", callback_data="bulk_amt_8")],
        [InlineKeyboardButton(text="10 lessons", callback_data="bulk_amt_10")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="bulk_back")],
    ]

    await state.update_data(
        teacher_id=teacher.id,
        student_id=student.id,
        student_name=student.name,
        origin=f"student_info-{student.id}",
    )
    await state.set_state(BulkPaymentStates.select_amount)

    await query.message.edit_text(
        f"\U0001f4b0 Deposit\n\n"
        f"Student: <b>{student.name}</b>\n"
        f"Current balance: <b>{student.paid_lessons_balance}</b> lesson(s)\n\n"
        "Select the number of lessons to deposit:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


@router.callback_query(F.data == 'my_balance')
async def student_my_balance(query: CallbackQuery, session: AsyncSession):
    """Student's own balance view"""
    await query.answer()
    result = await session.execute(select(Student).filter_by(telegram_id=query.from_user.id))
    student = result.scalar_one_or_none()
    if not student:
        await query.message.edit_text("You are not registered as a student.")
        return

    balance = student.paid_lessons_balance
    txns = await PaymentService.get_balance_history(session, student.id)

    lines = [
        f"💰 <b>My Balance</b>",
        f"Remaining: <b>{balance}</b> paid lesson(s)",
        "",
    ]

    if not txns:
        lines.append("No transaction history.")
    else:
        lines.append("<b>Transactions:</b>")
        for txn in txns:
            date_str = txn.created_at.strftime("%d.%m.%Y")
            type_icon = {
                "payment": "\U0001f4b5",
                "apply": "\u2705",
                "refund": "\U0001f504",
                "forfeit": "\U0001f525",
            }.get(txn.type, "\U00002753")
            amt_str = f"+{txn.amount}" if txn.amount > 0 else str(txn.amount)
            note = f" — {txn.note}" if txn.note else ""
            lines.append(
                f"  {type_icon} {date_str} {amt_str} "
                f"(balance: {txn.balance_before}\u2192{txn.balance_after}){note}"
            )

    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to main", callback_data="back_to_main")],
    ]

    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith('student_balance-'))
async def show_student_balance(query: CallbackQuery, session: AsyncSession):
    """Show student balance and transaction history with back-to-student button"""
    await query.answer()
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    student = await session.get(Student, student_id)
    if not student or student.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only view your own students.")
        return

    balance = student.paid_lessons_balance
    txns = await PaymentService.get_balance_history(session, student_id)

    lines = [
        f"💰 <b>Balance: {student.name}</b>",
        f"Remaining: <b>{balance}</b> lesson(s)",
        "",
    ]

    if not txns:
        lines.append("No transaction history.")
    else:
        lines.append("<b>Transactions:</b>")
        for txn in txns:
            date_str = txn.created_at.strftime("%d.%m.%Y")
            type_icon = {
                "payment": "\U0001f4b5",
                "apply": "\u2705",
                "refund": "\U0001f504",
                "forfeit": "\U0001f525",
            }.get(txn.type, "\U00002753")
            amt_str = f"+{txn.amount}" if txn.amount > 0 else str(txn.amount)
            note = f" — {txn.note}" if txn.note else ""
            lines.append(
                f"  {type_icon} {date_str} {amt_str} "
                f"(balance: {txn.balance_before}\u2192{txn.balance_after}){note}"
            )

    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to student", callback_data=f"student_info-{student_id}")],
    ]

    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith('delete_student-'))
async def delete_student_confirm(query: CallbackQuery, session: AsyncSession):
    """Show delete student confirmation"""
    await query.answer()
    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("🔒 This feature is only available for teachers.")
        return
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    result = await session.execute(select(Student).filter_by(id=student_id))
    student = result.scalar_one_or_none()
    if not student or student.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only delete your own students.")
        return
    
    keyboard = [
        [InlineKeyboardButton(text="🗑 Yes, delete", callback_data=f"confirm_delete_student-{student_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data='list_students')]
    ]
    await query.message.edit_text(
        "⚠️ Are you sure you want to delete this student? All their lessons will be deleted.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith('confirm_delete_student-'))
async def confirm_delete_student(query: CallbackQuery, session: AsyncSession):
    """Confirm and execute student deletion"""
    await query.answer()
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    
    result = await session.execute(select(Student).filter_by(id=student_id))
    student = result.scalar_one_or_none()
    if not student:
        await query.message.edit_text("⚠️ Student not found.")
        return

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher or student.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only delete your own students.")
        return

    await session.delete(student)
    await session.commit()
    await query.message.edit_text(f"✅ Student {student.name} has been deleted.")
