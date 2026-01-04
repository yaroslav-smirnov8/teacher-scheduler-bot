"""Бизнес-логика приложения"""
from datetime import datetime, date, time
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from models import Teacher, Student, Lesson
import logging

logger = logging.getLogger(__name__)


class LessonService:
    """Сервис для работы с уроками"""
    
    @staticmethod
    def check_time_conflict(session: Session, teacher_id: int, student_id: int,
                           lesson_date: date, lesson_time: time,
                           exclude_lesson_id: Optional[int] = None) -> Tuple[bool, str]:
        """Check for time conflict"""
        query_teacher = session.query(Lesson).filter(
            Lesson.teacher_id == teacher_id,
            Lesson.date == lesson_date,
            Lesson.time == lesson_time
        )
        query_student = session.query(Lesson).filter(
            Lesson.student_id == student_id,
            Lesson.date == lesson_date,
            Lesson.time == lesson_time
        )

        if exclude_lesson_id:
            query_teacher = query_teacher.filter(Lesson.id != exclude_lesson_id)
            query_student = query_student.filter(Lesson.id != exclude_lesson_id)

        if query_teacher.first():
            return False, "The teacher already has a lesson scheduled at this time"
        if query_student.first():
            return False, "The student already has a lesson scheduled at this time"

        return True, ""
    
    @staticmethod
    def create_lesson(session: Session, teacher_id: int, student_id: int,
                     lesson_date: date, lesson_time: time) -> Tuple[bool, str, Optional[Lesson]]:
        """Create lesson with validation"""
        if lesson_date < datetime.now().date():
            return False, "Cannot schedule a lesson for a past date", None

        is_valid, error_msg = LessonService.check_time_conflict(
            session, teacher_id, student_id, lesson_date, lesson_time
        )
        if not is_valid:
            return False, error_msg, None

        lesson = Lesson(
            date=lesson_date,
            time=lesson_time,
            teacher_id=teacher_id,
            student_id=student_id
        )
        session.add(lesson)
        session.commit()
        session.refresh(lesson)

        return True, "Lesson created successfully", lesson
    
    @staticmethod
    def reschedule_lesson(session: Session, lesson_id: int, new_time: time) -> Tuple[bool, str]:
        """Reschedule lesson"""
        lesson = session.query(Lesson).filter_by(id=lesson_id).first()
        if not lesson:
            return False, "Lesson not found"

        if lesson.date < datetime.now().date():
            return False, "Cannot reschedule a lesson in the past"

        is_valid, error_msg = LessonService.check_time_conflict(
            session, lesson.teacher_id, lesson.student_id,
            lesson.date, new_time, exclude_lesson_id=lesson_id
        )
        if not is_valid:
            return False, error_msg

        lesson.time = new_time
        session.commit()

        return True, "Lesson rescheduled successfully"
    
    @staticmethod
    def cancel_lesson(session: Session, lesson_id: int) -> Tuple[bool, str, Optional[Lesson]]:
        """Cancel lesson"""
        lesson = session.query(Lesson).filter_by(id=lesson_id).first()
        if not lesson:
            return False, "Lesson not found", None

        lesson_copy = lesson
        session.delete(lesson)
        session.commit()

        return True, "Lesson cancelled", lesson_copy
    
    @staticmethod
    def get_future_lessons(session: Session, student_id: int) -> List[Lesson]:
        """Получить будущие уроки ученика"""
        today = datetime.now().date()
        return session.query(Lesson).filter(
            Lesson.student_id == student_id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time).all()
    
    @staticmethod
    def get_lessons_by_date(session: Session, teacher_id: int, lesson_date: date) -> List[Lesson]:
        """Получить уроки преподавателя на дату"""
        return session.query(Lesson).filter(
            Lesson.teacher_id == teacher_id,
            Lesson.date == lesson_date
        ).order_by(Lesson.time).all()


class NotificationService:
    """Service for sending notifications"""

    @staticmethod
    def notify_student_lesson_created(bot, student: Student, teacher: Teacher,
                                     lesson_date: date, lesson_time: time) -> bool:
        """Notify student about lesson appointment"""
        if not student.telegram_id:
            return False

        try:
            bot.send_message(
                chat_id=student.telegram_id,
                text=f"You have a lesson scheduled with {teacher.name} on {lesson_date} at {lesson_time.strftime('%H:%M')}."
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification to student {student.id}: {e}")
            return False
    
    @staticmethod
    def notify_student_lesson_cancelled(bot, student: Student, teacher: Teacher,
                                       lesson_date: date, lesson_time: time) -> bool:
        """Notify student about lesson cancellation"""
        if not student.telegram_id:
            return False

        try:
            bot.send_message(
                chat_id=student.telegram_id,
                text=f"The lesson with {teacher.name} on {lesson_date} at {lesson_time.strftime('%H:%M')} has been cancelled."
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification to student {student.id}: {e}")
            return False
    
    @staticmethod
    def notify_student_reschedule_result(bot, student: Student, teacher: Teacher,
                                        lesson_date: date, new_time: time,
                                        accepted: bool) -> bool:
        """Notify student about reschedule result"""
        if not student.telegram_id:
            return False

        try:
            if accepted:
                text = f"Your lesson with {teacher.name} has been rescheduled to {lesson_date} at {new_time.strftime('%H:%M')}."
            else:
                text = f"Your request to reschedule the lesson with {teacher.name} was declined."

            bot.send_message(chat_id=student.telegram_id, text=text)
            return True
        except Exception as e:
            logger.error(f"Error sending notification to student {student.id}: {e}")
            return False
    
    @staticmethod
    def notify_teacher_reschedule_request(bot, teacher: Teacher, student: Student,
                                         lesson: Lesson, new_hour: int, reason: str,
                                         keyboard) -> bool:
        """Notify teacher about reschedule request"""
        if not teacher.telegram_id:
            return False

        try:
            bot.send_message(
                chat_id=teacher.telegram_id,
                text=f"Student {student.name} requests to reschedule the lesson from {lesson.time.strftime('%H:%M')} to {new_hour}:00 for reason: {reason}. Do you agree?",
                reply_markup=keyboard
            )
            return True
        except Exception as e:
            logger.error(f"Error sending notification to teacher {teacher.id}: {e}")
            return False


class UserService:
    """Service for working with users"""

    @staticmethod
    def get_teacher_by_telegram_id(session: Session, telegram_id: int) -> Optional[Teacher]:
        """Get teacher by telegram_id"""
        return session.query(Teacher).filter_by(telegram_id=telegram_id).first()

    @staticmethod
    def get_student_by_telegram_id(session: Session, telegram_id: int) -> Optional[Student]:
        """Get student by telegram_id"""
        return session.query(Student).filter_by(telegram_id=telegram_id).first()

    @staticmethod
    def get_teacher_students(session: Session, teacher_id: int) -> List[Student]:
        """Get teacher's students"""
        return session.query(Student).filter_by(teacher_id=teacher_id).all()
