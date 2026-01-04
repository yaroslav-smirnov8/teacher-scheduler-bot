"""Unit tests for ORM models."""

import pytest
from datetime import date, time
from sqlalchemy.exc import IntegrityError

from models import Teacher, Student, Lesson


def test_teacher_creation(test_session):
    """Test Teacher model creation."""
    teacher = Teacher(
        name="Jane Doe",
        contact_info="jane@example.com",
        login="janedoe",
        telegram_id=111222333
    )
    test_session.add(teacher)
    test_session.commit()
    
    assert teacher.id is not None
    assert teacher.name == "Jane Doe"
    assert teacher.login == "janedoe"
    assert teacher.telegram_id == 111222333


def test_teacher_student_relationship(test_session, sample_teacher):
    """Test Teacher-Student one-to-many relationship."""
    student1 = Student(name="Bob", teacher_id=sample_teacher.id, telegram_id=111)
    student2 = Student(name="Carol", teacher_id=sample_teacher.id, telegram_id=222)
    
    test_session.add_all([student1, student2])
    test_session.commit()
    
    test_session.refresh(sample_teacher)
    assert len(sample_teacher.students) == 2
    assert student1 in sample_teacher.students
    assert student2 in sample_teacher.students


def test_unique_telegram_id_constraint(test_session):
    """Test unique constraint on telegram_id."""
    teacher1 = Teacher(name="Teacher1", login="t1", telegram_id=999)
    test_session.add(teacher1)
    test_session.commit()
    
    teacher2 = Teacher(name="Teacher2", login="t2", telegram_id=999)
    test_session.add(teacher2)
    
    with pytest.raises(IntegrityError):
        test_session.commit()


def test_lesson_relationships(test_session, sample_teacher, sample_student):
    """Test Lesson model with foreign key relationships."""
    lesson = Lesson(
        date=date(2024, 3, 15),
        time=time(14, 0),
        teacher_id=sample_teacher.id,
        student_id=sample_student.id
    )
    test_session.add(lesson)
    test_session.commit()
    test_session.refresh(lesson)
    
    assert lesson.teacher.id == sample_teacher.id
    assert lesson.student.id == sample_student.id
    assert lesson.teacher.name == "John Doe"
    assert lesson.student.name == "Alice Smith"


def test_cascade_delete_teacher(test_session, sample_teacher, sample_student, sample_lesson):
    """Test cascade delete when teacher is deleted."""
    teacher_id = sample_teacher.id
    
    test_session.delete(sample_teacher)
    test_session.commit()
    
    assert test_session.query(Teacher).filter_by(id=teacher_id).first() is None
    assert test_session.query(Student).count() == 0
    assert test_session.query(Lesson).count() == 0


def test_cascade_delete_student(test_session, sample_teacher, sample_student, sample_lesson):
    """Test cascade delete when student is deleted."""
    student_id = sample_student.id
    teacher_id = sample_teacher.id
    
    test_session.delete(sample_student)
    test_session.commit()
    
    assert test_session.query(Student).filter_by(id=student_id).first() is None
    assert test_session.query(Lesson).count() == 0
    assert test_session.query(Teacher).filter_by(id=teacher_id).first() is not None


def test_not_null_constraints(test_session):
    """Test NOT NULL constraints on required fields."""
    teacher = Teacher(name="Test", login="test")
    test_session.add(teacher)
    
    with pytest.raises(IntegrityError):
        test_session.commit()
    
    test_session.rollback()
    
    lesson = Lesson(time=time(10, 0), teacher_id=1, student_id=1)
    test_session.add(lesson)
    
    with pytest.raises(IntegrityError):
        test_session.commit()


def test_date_time_column_types(test_session, sample_teacher, sample_student):
    """Test date and time column types."""
    lesson_date = date(2024, 6, 15)
    lesson_time = time(16, 30)
    
    lesson = Lesson(
        date=lesson_date,
        time=lesson_time,
        teacher_id=sample_teacher.id,
        student_id=sample_student.id
    )
    test_session.add(lesson)
    test_session.commit()
    test_session.refresh(lesson)
    
    assert isinstance(lesson.date, date)
    assert isinstance(lesson.time, time)
    assert lesson.date == lesson_date
    assert lesson.time == lesson_time
