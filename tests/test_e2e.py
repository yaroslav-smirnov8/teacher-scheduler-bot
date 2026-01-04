"""End-to-end tests for complete user workflows."""

import pytest
from datetime import date, time, datetime, timedelta

from services import LessonService, NotificationService
from models import Teacher, Student, Lesson


def test_complete_registration_and_booking_flow(test_session, mock_bot):
    """Test complete registration and booking flow."""
    teacher = Teacher(name="John Doe", login="john", telegram_id=123456)
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)
    
    student = Student(name="Alice", teacher_id=teacher.id, telegram_id=789012)
    test_session.add(student)
    test_session.commit()
    test_session.refresh(student)
    
    tomorrow = date.today() + timedelta(days=1)
    success, message, lesson = LessonService.create_lesson(
        test_session, teacher.id, student.id, tomorrow, time(15, 0)
    )
    
    assert success is True
    
    result = NotificationService.notify_student_lesson_created(
        mock_bot, student, teacher, tomorrow, time(15, 0)
    )
    
    assert result is True
    mock_bot.send_message.assert_called_once()


def test_reschedule_approval_workflow(test_session, mock_bot):
    """Test reschedule approval workflow."""
    teacher = Teacher(name="John", login="john", telegram_id=123)
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)

    student = Student(name="Alice", telegram_id=456, teacher_id=teacher.id)
    test_session.add(student)
    test_session.commit()
    test_session.refresh(student)
    
    tomorrow = date.today() + timedelta(days=1)
    lesson = Lesson(date=tomorrow, time=time(15, 0), teacher_id=teacher.id, student_id=student.id)
    test_session.add(lesson)
    test_session.commit()
    test_session.refresh(lesson)
    
    new_time = time(16, 0)
    success, message = LessonService.reschedule_lesson(test_session, lesson.id, new_time)
    
    assert success is True
    test_session.refresh(lesson)
    assert lesson.time == new_time
    
    result = NotificationService.notify_student_reschedule_result(
        mock_bot, student, teacher, tomorrow, new_time, accepted=True
    )
    
    assert result is True


def test_reschedule_denial_workflow(test_session, mock_bot):
    """Test reschedule denial workflow."""
    teacher = Teacher(name="John", login="john", telegram_id=123)
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)

    student = Student(name="Alice", telegram_id=456, teacher_id=teacher.id)
    test_session.add(student)
    test_session.commit()
    test_session.refresh(student)
    
    tomorrow = date.today() + timedelta(days=1)
    original_time = time(15, 0)
    lesson = Lesson(date=tomorrow, time=original_time, teacher_id=teacher.id, student_id=student.id)
    test_session.add(lesson)
    test_session.commit()
    test_session.refresh(lesson)
    
    result = NotificationService.notify_student_reschedule_result(
        mock_bot, student, teacher, tomorrow, original_time, accepted=False
    )
    
    assert result is True
    test_session.refresh(lesson)
    assert lesson.time == original_time


def test_conflict_prevention_flow(test_session):
    """Test conflict prevention flow."""
    teacher = Teacher(name="John", login="john", telegram_id=123)
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)

    student1 = Student(name="Alice", telegram_id=456, teacher_id=teacher.id)
    student2 = Student(name="Bob", telegram_id=789, teacher_id=teacher.id)
    test_session.add_all([student1, student2])
    test_session.commit()
    test_session.refresh(student1)
    test_session.refresh(student2)
    
    tomorrow = date.today() + timedelta(days=1)
    lesson_time = time(15, 0)
    
    success1, message1, lesson1 = LessonService.create_lesson(
        test_session, teacher.id, student1.id, tomorrow, lesson_time
    )
    assert success1 is True
    
    success2, message2, lesson2 = LessonService.create_lesson(
        test_session, teacher.id, student2.id, tomorrow, lesson_time
    )
    
    assert success2 is False
    assert "already has a lesson" in message2


def test_cancellation_flow(test_session, mock_bot):
    """Test cancellation flow."""
    teacher = Teacher(name="John", login="john", telegram_id=123)
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)

    student = Student(name="Alice", telegram_id=456, teacher_id=teacher.id)
    test_session.add(student)
    test_session.commit()
    test_session.refresh(student)
    
    tomorrow = date.today() + timedelta(days=1)
    lesson = Lesson(date=tomorrow, time=time(15, 0), teacher_id=teacher.id, student_id=student.id)
    test_session.add(lesson)
    test_session.commit()
    lesson_id = lesson.id
    
    success, message, lesson_copy = LessonService.cancel_lesson(test_session, lesson_id)
    
    assert success is True
    assert test_session.query(Lesson).filter_by(id=lesson_id).first() is None
    
    result = NotificationService.notify_student_lesson_cancelled(
        mock_bot, student, teacher, tomorrow, time(15, 0)
    )
    
    assert result is True


def test_multiple_students_same_teacher(test_session):
    """Test teacher managing multiple students."""
    teacher = Teacher(name="John", login="john", telegram_id=123)
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)
    
    students = []
    for i in range(3):
        student = Student(name=f"Student{i}", teacher_id=teacher.id, telegram_id=1000+i)
        test_session.add(student)
        students.append(student)
    test_session.commit()
    
    tomorrow = date.today() + timedelta(days=1)
    times = [time(9, 0), time(12, 0), time(15, 0)]
    
    for student, t in zip(students, times):
        test_session.refresh(student)
        success, message, lesson = LessonService.create_lesson(
            test_session, teacher.id, student.id, tomorrow, t
        )
        assert success is True
    
    lessons = test_session.query(Lesson).filter_by(teacher_id=teacher.id, date=tomorrow).all()
    assert len(lessons) == 3


def test_same_time_different_days(test_session, sample_teacher, sample_student):
    """Test booking same time slot on different days."""
    base_date = date.today() + timedelta(days=1)
    lesson_time = time(15, 0)
    
    for i in range(3):
        lesson_date = base_date + timedelta(days=i)
        success, message, lesson = LessonService.create_lesson(
            test_session, sample_teacher.id, sample_student.id, lesson_date, lesson_time
        )
        assert success is True
    
    lessons = test_session.query(Lesson).filter_by(
        teacher_id=sample_teacher.id,
        time=lesson_time
    ).all()
    assert len(lessons) == 3


def test_past_date_rejection(test_session, sample_teacher, sample_student):
    """Test rejection of past date bookings."""
    yesterday = date.today() - timedelta(days=1)
    
    success, message, lesson = LessonService.create_lesson(
        test_session, sample_teacher.id, sample_student.id, yesterday, time(15, 0)
    )
    
    assert success is False
    assert "past date" in message
    assert lesson is None
