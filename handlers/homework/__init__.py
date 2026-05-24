"""Homework handlers package"""
from handlers.homework.teacher import (
    TeacherHomeworkStates,
    teacher_view_homework_history, teacher_homework_menu, teacher_select_lesson,
    teacher_edit_homework_text, teacher_confirm_homework,
    teacher_view_homework_detail, teacher_mark_homework, teacher_toggle_optional,
    teacher_homework_stats, teacher_student_homework_stats,
)
from handlers.homework.student import (
    StudentHomeworkStates,
    student_homework_menu, student_view_homework_detail,
    student_mark_homework_received, student_mark_homework_completed,
)
from handlers.homework.common import cancel_handler, back_handler

__all__ = [
    'TeacherHomeworkStates', 'StudentHomeworkStates',
    'teacher_view_homework_history', 'teacher_homework_menu', 'teacher_select_lesson',
    'teacher_edit_homework_text', 'teacher_confirm_homework',
    'teacher_view_homework_detail', 'teacher_mark_homework', 'teacher_toggle_optional',
    'teacher_homework_stats', 'teacher_student_homework_stats',
    'student_homework_menu', 'student_view_homework_detail',
    'student_mark_homework_received', 'student_mark_homework_completed',
    'cancel_handler', 'back_handler',
]
