"""Calendar keyboard builder with lesson indicators"""
import calendar
from datetime import datetime, date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATA_IGNORE = "IGNORE"


def create_calendar(
    year: int = None,
    month: int = None,
    lesson_data: dict = None
) -> InlineKeyboardMarkup:
    """Create calendar keyboard with lesson indicators.
    
    Args:
        year: Year to display
        month: Month to display
        lesson_data: Dict mapping date strings (YYYY-MM-DD) to dict with 'count', 'has_unpaid', 'all_paid'
                    e.g., {'2025-01-15': {'count': 2, 'has_unpaid': False, 'all_paid': True}}
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    keyboard = []

    # Month and Year
    keyboard.append([
        InlineKeyboardButton(
            text="\U0001f4c6 " + calendar.month_name[month] + " " + str(year),
            callback_data=DATA_IGNORE
        )
    ])

    # Days of week
    keyboard.append([
        InlineKeyboardButton(text=day, callback_data=DATA_IGNORE)
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    ])

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=DATA_IGNORE))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                day_info = lesson_data.get(date_str, {'count': 0, 'has_unpaid': False}) if lesson_data else {'count': 0, 'has_unpaid': False}
                lesson_count = day_info.get('count', 0)
                has_unpaid = day_info.get('has_unpaid', False)

                if has_unpaid:
                    day_text = f"{day} \U0001f534"
                elif lesson_count > 0:
                    all_paid = day_info.get('all_paid', False)
                    if all_paid and lesson_count > 1:
                        day_text = f"{day} \U0001f7e1"
                    elif all_paid:
                        day_text = f"{day} \U0001f7e2"
                    else:
                        day_text = f"{day} \U0001f534"
                else:
                    day_text = str(day)

                row.append(InlineKeyboardButton(
                    text=day_text,
                    callback_data=f"CALENDAR-DAY-{year}-{month}-{day}"
                ))
        keyboard.append(row)

    # Navigation
    prev_month, prev_year = (month - 1, year) if month > 1 else (12, year - 1)
    next_month, next_year = (month + 1, year) if month < 12 else (1, year + 1)

    keyboard.append([
        InlineKeyboardButton(text="◀️", callback_data=f"PREV-MONTH-{prev_year}-{prev_month}"),
        InlineKeyboardButton(text=" ", callback_data=DATA_IGNORE),
        InlineKeyboardButton(text="▶️", callback_data=f"NEXT-MONTH-{next_year}-{next_month}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_time_keyboard(start_hour: int = 6, end_hour: int = 23, back_callback: str = None) -> InlineKeyboardMarkup:
    """Build time selection keyboard (hourly slots)"""
    keyboard = []
    for hour in range(start_hour, end_hour + 1):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{hour}:00",
                callback_data=f"TIME-SLOT-{hour}"
            )
        ])
    # Add in a grid of 3 columns for compactness
    rows = []
    for i in range(0, len(keyboard), 3):
        row = [keyboard[i][0]]
        if i + 1 < len(keyboard):
            row.append(keyboard[i + 1][0])
        if i + 2 < len(keyboard):
            row.append(keyboard[i + 2][0])
        rows.append(row)
    last_row = []
    if back_callback:
        last_row.append(InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback))
    last_row.append(InlineKeyboardButton(text="❌ Cancel", callback_data="CANCEL-CONV"))
    rows.append(last_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)