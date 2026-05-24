"""Bulk payment FSM — teacher pays for N future lessons"""
import logging
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from models import Teacher, Student
from payment_service import PaymentService

logger = logging.getLogger(__name__)


class BulkPaymentStates(StatesGroup):
    select_student = State()
    select_amount = State()


async def bulk_payment_start(query: CallbackQuery, state: FSMContext, session) -> None:
    """Start bulk payment: show student list."""
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
        keyboard = [
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Payments", callback_data="pay_menu")],
        ]
        await query.message.edit_text(
            "No students found. Add a student first.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        return

    keyboard = [
        [InlineKeyboardButton(text=s.name, callback_data=f"bulk_student_{s.id}")]
        for s in students
    ]
    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="pay_menu")])

    await query.message.edit_text(
        "\U0001f4e6 Bulk Payment\n\nSelect a student:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(BulkPaymentStates.select_student)
    await state.update_data(teacher_id=teacher.id)


async def bulk_select_student(query: CallbackQuery, state: FSMContext, session) -> None:
    student_id_str = query.data.replace("bulk_student_", "")
    if not student_id_str.isdigit():
        await query.answer("Invalid student", show_alert=True)
        return
    student_id = int(student_id_str)

    data = await state.get_data()
    teacher_id = data.get("teacher_id")
    if not teacher_id:
        await query.answer("Session expired. Please start again.", show_alert=True)
        return

    student = await session.get(Student, student_id)
    if not student:
        await query.answer("Student not found", show_alert=True)
        return

    if student.teacher_id != teacher_id:
        await query.answer("Access denied", show_alert=True)
        return

    await state.update_data(student_id=student_id, student_name=student.name)

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

    data = await state.get_data()
    balance = student.paid_lessons_balance

    await query.message.edit_text(
        f"\U0001f4e6 Bulk Payment\n\n"
        f"Student: <b>{student.name}</b>\n"
        f"Current balance: <b>{balance}</b> remaining lesson(s)\n\n"
        "Select the number of lessons to pay for:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(BulkPaymentStates.select_amount)


async def bulk_select_amount(query: CallbackQuery, state: FSMContext, session) -> None:
    amt_str = query.data.replace("bulk_amt_", "")
    if not amt_str.isdigit():
        await query.answer("Invalid amount", show_alert=True)
        return
    amount = int(amt_str)

    data = await state.get_data()
    teacher_id = data["teacher_id"]
    student_id = data["student_id"]
    student_name = data.get("student_name", "Student")
    origin = data.get("origin", "pay_menu")

    success, message = await PaymentService.create_bulk_payment(
        session, teacher_id, student_id, amount,
    )

    if not success:
        await query.message.edit_text(
            f"\u274c {message}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\U0001f504 Try Again", callback_data="pay_menu")],
            ]),
        )
        await state.clear()
        return

    await state.clear()

    student = await session.get(Student, student_id)
    balance = student.paid_lessons_balance if student else 0

    await query.message.edit_text(
        f"\u2705 <b>{message}</b>\n\n"
        f"Student: <b>{student_name}</b>\n"
        f"New balance: <b>{balance}</b> lesson(s) remaining",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f4b3 Back", callback_data=origin)],
        ]),
    )


async def bulk_back(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    origin = data.get("origin", "pay_menu")
    await state.clear()
    if origin.startswith("student_info-"):
        from bot.routers.calendar.students import _render_student_card
        student_id = int(origin.split("-")[-1])
        student = await session.get(Student, student_id)
        if student:
            await _render_student_card(query, session, student)
        else:
            from handlers.payment import payment_menu
            await payment_menu(query, state, session)
    else:
        from handlers.payment import payment_menu
        await payment_menu(query, state, session)
