"""Reschedule router package"""
from bot.routers.reschedule.old_flow import router as old_flow_router
from bot.routers.reschedule.student_flow import router as student_flow_router
from bot.routers.reschedule.teacher_actions import router as teacher_actions_router
from bot.routers.reschedule.student_flow import StudentReschedule
from bot.routers.reschedule.old_flow import OldReschedule

__all__ = [
    'old_flow_router',
    'student_flow_router',
    'teacher_actions_router',
    'StudentReschedule',
    'OldReschedule',
]
