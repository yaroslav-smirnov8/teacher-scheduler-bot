"""Constants and helper functions for recurring lesson handlers"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Conversation states for recurring lesson creation
(
    RECURRING_SELECT_STUDENT, RECURRING_SELECT_FREQUENCY, RECURRING_SELECT_WEEKDAY,
    RECURRING_SELECT_DAY_OF_MONTH, RECURRING_SELECT_TIME, RECURRING_SELECT_END_DATE,
    RECURRING_CONFIRM
) = [str(i) for i in range(170, 177)]

# States for convert-to-recurring conversation
(
    CONVERT_SELECT_FREQUENCY, CONVERT_SELECT_END_DATE, CONVERT_CONFIRM
) = [str(i) for i in range(180, 183)]

# Back callback constants for each flow
REC_BACK_STUDENT = "REC-BACK-student"
REC_BACK_FREQUENCY = "REC-BACK-frequency"
REC_BACK_WEEKDAY = "REC-BACK-weekday"
REC_BACK_DAY = "REC-BACK-day"
REC_BACK_TIME = "REC-BACK-time"
REC_BACK_END_DATE = "REC-BACK-enddate"
CONV_BACK_FREQ = "CONV-BACK-freq"
CONV_BACK_END_DATE = "CONV-BACK-enddate"
CONV_BACK_LESSON = "CONV-BACK-lesson"


async def _append_back_button(keyboard: list, callback_data: str) -> list:
    """Append a Back button and Cancel button to keyboard"""
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=callback_data),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
    ])
    return keyboard
