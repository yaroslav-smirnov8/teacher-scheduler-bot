"""Tests for RescheduleService"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, date, time, timedelta
from sqlalchemy import select

from database import SessionLocal, init_db
from models import Teacher, Student, Lesson, RescheduleRequest
from services.reschedule_service import RescheduleService
from services.lesson_service import LessonService


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session"""
    await init_db()
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_check_reschedule_limit_under_limit(db_session):
    """Test that reschedule limit check passes when under limit"""
    # Create a teacher and student
    teacher = Teacher(name="Test Teacher", contact_info="test@test.com", login="testteacher", telegram_id=12345)
    student = Student(name="Test Student", telegram_id=54321, teacher=teacher)
    db_session.add(teacher)
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
    
    # Check limit (should pass with 0 requests)
    can_request, message = await RescheduleService.check_reschedule_limit(db_session, student.id)
    assert can_request is True
    assert message == ""


@pytest.mark.asyncio
async def test_check_reschedule_limit_at_limit(db_session):
    """Test that reschedule limit check fails when at limit (2 requests in 7 days)"""
    # Create a teacher and student
    teacher = Teacher(name="Test Teacher", contact_info="test@test.com", login="testteacher2", telegram_id=12346)
    student = Student(name="Test Student", telegram_id=54322, teacher=teacher)
    db_session.add(teacher)
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
    
    # Create 2 reschedule requests within the last 7 days
    for i in range(2):
        request = RescheduleRequest(
            lesson_id=1,
            student_id=student.id,
            teacher_id=teacher.id,
            original_date=date.today(),
            original_time=time(10, 0),
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(11, 0),
            reason="Test reason",
            status="pending",
            created_at=datetime.utcnow()
        )
        db_session.add(request)
    await db_session.commit()
    
    # Check limit (should fail with 2 requests)
    can_request, message = await RescheduleService.check_reschedule_limit(db_session, student.id)
    assert can_request is False
    assert "weekly limit" in message.lower()


@pytest.mark.asyncio
async def test_check_reschedule_limit_old_requests(db_session):
    """Test that old requests (older than 7 days) don't count against limit"""
    # Create a teacher and student
    teacher = Teacher(name="Test Teacher", contact_info="test@test.com", login="testteacher3", telegram_id=12347)
    student = Student(name="Test Student", telegram_id=54323, teacher=teacher)
    db_session.add(teacher)
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
    
    # Create 2 reschedule requests older than 7 days
    eight_days_ago = datetime.utcnow() - timedelta(days=8)
    for i in range(2):
        request = RescheduleRequest(
            lesson_id=1,
            student_id=student.id,
            teacher_id=teacher.id,
            original_date=date.today(),
            original_time=time(10, 0),
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(11, 0),
            reason="Test reason",
            status="pending",
            created_at=eight_days_ago
        )
        db_session.add(request)
    await db_session.commit()
    
    # Check limit (should pass since requests are old)
    can_request, message = await RescheduleService.check_reschedule_limit(db_session, student.id)
    assert can_request is True
    assert message == ""


@pytest.mark.asyncio
async def test_create_reschedule_request(db_session):
    """Test creating a reschedule request"""
    # Create a teacher and student
    teacher = Teacher(name="Test Teacher", contact_info="test@test.com", login="testteacher4", telegram_id=12348)
    student = Student(name="Test Student", telegram_id=54324, teacher=teacher)
    db_session.add(teacher)
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(teacher)
    await db_session.refresh(student)
    
    # Create a lesson
    lesson_date = date.today() + timedelta(days=2)
    lesson_time = time(10, 0)
    lesson = Lesson(
        date=lesson_date,
        time=lesson_time,
        teacher_id=teacher.id,
        student_id=student.id
    )
    db_session.add(lesson)
    await db_session.commit()
    await db_session.refresh(lesson)
    
    # Create reschedule request
    requested_date = date.today() + timedelta(days=3)
    requested_time = time(11, 0)
    success, message, request = await RescheduleService.create_reschedule_request(
        db_session, lesson.id, student.id, teacher.id,
        lesson_date, lesson_time, requested_date, requested_time, "Need to reschedule"
    )
    
    assert success is True
    assert request is not None
    assert request.status == "pending"
    assert request.lesson_id == lesson.id
    assert request.student_id == student.id
    assert request.teacher_id == teacher.id


@pytest.mark.asyncio
async def test_approve_reschedule(db_session):
    """Test approving a reschedule request"""
    # Create a teacher and student
    teacher = Teacher(name="Test Teacher", contact_info="test@test.com", login="testteacher5", telegram_id=12349)
    student = Student(name="Test Student", telegram_id=54325, teacher=teacher)
    db_session.add(teacher)
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(teacher)
    await db_session.refresh(student)
    
    # Create a lesson
    lesson_date = date.today() + timedelta(days=2)
    lesson_time = time(10, 0)
    lesson = Lesson(
        date=lesson_date,
        time=lesson_time,
        teacher_id=teacher.id,
        student_id=student.id
    )
    db_session.add(lesson)
    await db_session.commit()
    await db_session.refresh(lesson)
    
    # Create a reschedule request
    requested_date = date.today() + timedelta(days=3)
    requested_time = time(11, 0)
    request = RescheduleRequest(
        lesson_id=lesson.id,
        student_id=student.id,
        teacher_id=teacher.id,
        original_date=lesson_date,
        original_time=lesson_time,
        requested_date=requested_date,
        requested_time=requested_time,
        reason="Test reason",
        status="pending",
        created_at=datetime.utcnow()
    )
    db_session.add(request)
    await db_session.commit()
    await db_session.refresh(request)
    
    # Approve the request
    success, message, updated_lesson = await RescheduleService.approve_reschedule(db_session, request.id)
    
    assert success is True
    assert updated_lesson is not None
    assert updated_lesson.date == requested_date
    assert updated_lesson.time == requested_time
    
    # Check request status
    await db_session.refresh(request)
    assert request.status == "approved"


@pytest.mark.asyncio
async def test_decline_reschedule(db_session):
    """Test declining a reschedule request"""
    # Create a teacher and student
    teacher = Teacher(name="Test Teacher", contact_info="test@test.com", login="testteacher6", telegram_id=12350)
    student = Student(name="Test Student", telegram_id=54326, teacher=teacher)
    db_session.add(teacher)
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(teacher)
    await db_session.refresh(student)
    
    # Create a lesson
    lesson_date = date.today() + timedelta(days=2)
    lesson_time = time(10, 0)
    lesson = Lesson(
        date=lesson_date,
        time=lesson_time,
        teacher_id=teacher.id,
        student_id=student.id
    )
    db_session.add(lesson)
    await db_session.commit()
    await db_session.refresh(lesson)
    
    # Create a reschedule request
    requested_date = date.today() + timedelta(days=3)
    requested_time = time(11, 0)
    request = RescheduleRequest(
        lesson_id=lesson.id,
        student_id=student.id,
        teacher_id=teacher.id,
        original_date=lesson_date,
        original_time=lesson_time,
        requested_date=requested_date,
        requested_time=requested_time,
        reason="Test reason",
        status="pending",
        created_at=datetime.utcnow()
    )
    db_session.add(request)
    await db_session.commit()
    await db_session.refresh(request)
    
    # Decline the request
    success, message = await RescheduleService.decline_reschedule(db_session, request.id)
    
    assert success is True
    
    # Check request status
    await db_session.refresh(request)
    assert request.status == "declined"
    
    # Check lesson time remains unchanged
    await db_session.refresh(lesson)
    assert lesson.date == lesson_date
    assert lesson.time == lesson_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
