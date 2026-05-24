"""Calendar router package"""
from bot.routers.calendar.display import router as display_router
from bot.routers.calendar.students import router as students_router
from bot.routers.calendar.schedule import router as schedule_router
from bot.routers.calendar.schedule import ScheduleLesson
from bot.routers.calendar.display import get_month_lesson_data

__all__ = [
    'display_router',
    'students_router',
    'schedule_router',
    'ScheduleLesson',
    'get_month_lesson_data',
]
