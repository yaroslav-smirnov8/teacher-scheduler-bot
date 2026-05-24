"""Balance history view — show remaining prepaid lessons and transaction log"""
import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from models import Teacher, Student
from payment_service import PaymentService

logger = logging.getLogger(__name__)


async def balance_menu(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show student list for viewing balance."""
    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    result = await session.execute(
        select(Student).where(Student.teacher_id == teacher.id).order_by(Student.name)
    )
    students = result.scalars().all()

    if not students:
        await query.message.edit_text(
            "No students found.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")],
            ]),
        )
        return

    keyboard = []
    for s in students:
        label = f"{s.name} (\U0001f4b0 {s.paid_lessons_balance} remaining)"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"bal_student_{s.id}")])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="pay_menu")])

    await query.message.edit_text(
        "\U0001f4b0 Balance History\n\nSelect a student to view payment history:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def balance_show_student(query: CallbackQuery, state: FSMContext, session) -> None:
    student_id_str = query.data.replace("bal_student_", "")
    if not student_id_str.isdigit():
        await query.answer("Invalid student", show_alert=True)
        return
    student_id = int(student_id_str)

    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("You are not registered as a teacher.", show_alert=True)
        return

    student = await session.get(Student, student_id)
    if not student:
        await query.answer("Student not found", show_alert=True)
        return

    if student.teacher_id != teacher.id:
        await query.answer("Access denied", show_alert=True)
        return

    balance = student.paid_lessons_balance
    txns = await PaymentService.get_balance_history(session, student_id)

    lines = [
        f"\U0001f4b0 <b>Balance History</b>",
        f"Student: <b>{student.name}</b>",
        f"Remaining: <b>{balance}</b> lesson(s)",
        "",
    ]

    if not txns:
        lines.append("No payment history yet.")
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

    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Students", callback_data="bal_menu")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")],
        ]),
    )
