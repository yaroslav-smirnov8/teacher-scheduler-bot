"""Integration tests for services with real database."""

import pytest
from datetime import date, time, datetime, timedelta

from services import LessonService
from models import Teacher, Student, Lesson


def test_full_booking_workflow(test_session):
    """Test complete booking workflow."""
    teacher = Teacher(name="John", login="john", telegram_id=123)
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)
    
    student = Student(name="Alice", teacher_id=teacher.id, telegram_id=456)
    test_session.add(student)
    test_session.commit()
    test_session.refresh(student)
    
    tomorrow = date.today() + timedelta(days=1)
    success, message, lesson = LessonService.create_lesson(
        test_session, teacher.id, student.id, tomorrow, time(15, 0)
    )
    
    assert success is True
    assert lesson is not None
    assert lesson.teacher_id == teacher.id
    assert lesson.student_id == student.id


def test_concurrent_booking_attempts(test_session, sample_teacher, sample_student):
    """Test concurrent booking attempts for same slot."""
    tomorrow = date.today() + timedelta(days=1)
    lesson_time = time(15, 0)
    
    success1, message1, lesson1 = LessonService.create_lesson(
        test_session, sample_teacher.id, sample_student.id, tomorrow, lesson_time
    )
    
    assert success1 is True
    
    student2 = Student(name="Bob", teacher_id=sample_teacher.id, telegram_id=999)
    test_session.add(student2)
    test_session.commit()
    test_session.refresh(student2)
    
    success2, message2, lesson2 = LessonService.create_lesson(
        test_session, sample_teacher.id, student2.id, tomorrow, lesson_time
    )
    
    assert success2 is False
    assert "already has a lesson" in message2


def test_reschedule_with_conflict(test_session, sample_teacher, sample_student, sample_lesson):
    """Test rescheduling to occupied time slot."""
    tomorrow = date.today() + timedelta(days=1)
    lesson2 = Lesson(
        date=tomorrow,
        time=time(16, 0),
        teacher_id=sample_teacher.id,
        student_id=sample_student.id
    )
    test_session.add(lesson2)
    test_session.commit()
    test_session.refresh(lesson2)
    
    success, message = LessonService.reschedule_lesson(
        test_session, lesson2.id, time(15, 0)
    )
    
    assert success is False
    assert "already has a lesson" in message


def test_cascade_delete_teacher(test_session, sample_teacher, sample_student, sample_lesson):
    """Test cascade delete when teacher deleted."""
    teacher_id = sample_teacher.id
    
    test_session.delete(sample_teacher)
    test_session.commit()
    
    assert test_session.query(Teacher).filter_by(id=teacher_id).first() is None
    assert test_session.query(Student).count() == 0
    assert test_session.query(Lesson).count() == 0


def test_cascade_delete_student(test_session, sample_teacher, sample_student, sample_lesson):
    """Test cascade delete when student deleted."""
    student_id = sample_student.id
    teacher_id = sample_teacher.id
    
    test_session.delete(sample_student)
    test_session.commit()
    
    assert test_session.query(Student).filter_by(id=student_id).first() is None
    assert test_session.query(Lesson).count() == 0
    assert test_session.query(Teacher).filter_by(id=teacher_id).first() is not None


def test_get_teacher_schedule(test_session, sample_teacher, sample_student):
    """Test retrieving teacher's schedule for specific date."""
    tomorrow = date.today() + timedelta(days=1)
    
    lesson1 = Lesson(date=tomorrow, time=time(9, 0), teacher_id=sample_teacher.id, student_id=sample_student.id)
    lesson2 = Lesson(date=tomorrow, time=time(15, 0), teacher_id=sample_teacher.id, student_id=sample_student.id)
    lesson3 = Lesson(date=tomorrow, time=time(11, 0), teacher_id=sample_teacher.id, student_id=sample_student.id)
    
    test_session.add_all([lesson1, lesson2, lesson3])
    test_session.commit()
    
    lessons = LessonService.get_lessons_by_date(test_session, sample_teacher.id, tomorrow)
    
    assert len(lessons) == 3
    assert lessons[0].time == time(9, 0)
    assert lessons[1].time == time(11, 0)
    assert lessons[2].time == time(15, 0)


def test_get_student_schedule(test_session, sample_teacher, sample_student):
    """Test retrieving student's future lessons."""
    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)
    
    past_lesson = Lesson(date=yesterday, time=time(15, 0), teacher_id=sample_teacher.id, student_id=sample_student.id)
    future_lesson = Lesson(date=tomorrow, time=time(15, 0), teacher_id=sample_teacher.id, student_id=sample_student.id)
    
    test_session.add_all([past_lesson, future_lesson])
    test_session.commit()
    
    lessons = LessonService.get_future_lessons(test_session, sample_student.id)
    
    assert len(lessons) == 1
    assert lessons[0].date == tomorrow


def test_multiple_lessons_same_day(test_session, sample_teacher, sample_student):
    """Test creating multiple lessons on same day."""
    tomorrow = date.today() + timedelta(days=1)
    times = [time(9, 0), time(12, 0), time(15, 0)]
    
    for t in times:
        success, message, lesson = LessonService.create_lesson(
            test_session, sample_teacher.id, sample_student.id, tomorrow, t
        )
        assert success is True
    
    lessons = test_session.query(Lesson).filter_by(date=tomorrow).all()
    assert len(lessons) == 3


def test_reschedule_to_same_time(test_session, sample_lesson):
    """Test rescheduling lesson to its current time."""
    original_time = sample_lesson.time
    
    success, message = LessonService.reschedule_lesson(
        test_session, sample_lesson.id, original_time
    )
    
    assert success is True
