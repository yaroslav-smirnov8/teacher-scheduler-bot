"""Payment handlers"""
import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.payment import (
    payment_menu, payment_show_unpaid, payment_show_upcoming, payment_show_recent,
    payment_show_lesson_details, payment_mark_paid, payment_mark_unpaid,
    payment_edit_note_start, payment_edit_note_save, payment_send_reminder,
    payment_cancel, PaymentNoteStates,
    payment_refund_lesson, payment_forfeit_lesson,
    BulkPaymentStates, bulk_payment_start, bulk_select_student, bulk_select_amount, bulk_back,
    balance_menu, balance_show_student,
)
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == 'pay_menu')
async def payment_menu_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    try:
        await payment_menu(query, state, session)
    except Exception:
        pass


@router.callback_query(F.data == 'pay_unpaid')
async def payment_unpaid_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_show_unpaid(query, state, session)


@router.callback_query(F.data == 'pay_upcoming')
async def payment_upcoming_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_show_upcoming(query, state, session)


@router.callback_query(F.data == 'pay_recent')
async def payment_recent_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_show_recent(query, state, session)


@router.callback_query(F.data.startswith('pay_lesson:'))
async def payment_lesson_details(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_show_lesson_details(query, state, session)


@router.callback_query(F.data.startswith('pay_mark_paid:'))
async def payment_mark_paid_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_mark_paid(query, state, session)


@router.callback_query(F.data.startswith('pay_mark_unpaid:'))
async def payment_mark_unpaid_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_mark_unpaid(query, state, session)


@router.callback_query(F.data.startswith('pay_send_reminder:'))
async def payment_send_reminder_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_send_reminder(query, state, session)


@router.callback_query(F.data.startswith('pay_refund:'))
async def payment_refund_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_refund_lesson(query, state, session)


@router.callback_query(F.data.startswith('pay_forfeit:'))
async def payment_forfeit_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_forfeit_lesson(query, state, session)


@router.callback_query(F.data.startswith('pay_edit_note:'))
async def payment_edit_note_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_edit_note_start(query, state, session)


@router.message(StateFilter(PaymentNoteStates.waiting_for_note))
async def payment_edit_note_save_handler(message, state: FSMContext, session: AsyncSession):
    await payment_edit_note_save(message, state, session)


@router.callback_query(F.data == 'pay_cancel')
async def payment_cancel_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await payment_cancel(query, state, session)


# ═══════════════════════════════════════════════════════════════════
# BULK PAYMENT
# ═══════════════════════════════════════════════════════════════════


@router.callback_query(F.data == 'bulk_start')
async def bulk_start_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await bulk_payment_start(query, state, session)


@router.callback_query(BulkPaymentStates.select_student, F.data.startswith('bulk_student_'))
async def bulk_student_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await bulk_select_student(query, state, session)


@router.callback_query(BulkPaymentStates.select_amount, F.data.startswith('bulk_amt_'))
async def bulk_amount_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await bulk_select_amount(query, state, session)


@router.callback_query(F.data == 'bulk_back')
async def bulk_back_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await bulk_back(query, state, session)


# ═══════════════════════════════════════════════════════════════════
# BALANCE HISTORY
# ═══════════════════════════════════════════════════════════════════


@router.callback_query(F.data == 'bal_menu')
async def balance_menu_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await balance_menu(query, state, session)


@router.callback_query(F.data.startswith('bal_student_'))
async def balance_student_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await balance_show_student(query, state, session)
