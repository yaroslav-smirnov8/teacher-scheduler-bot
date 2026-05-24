"""
Tests for Homework Service
"""
import pytest
import asyncio
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base, Teacher, Student, Lesson, Homework
from homework_service import HomeworkService


# Test database setup
@pytest.fixture
async def test_session():
    """Create an in-memory test database"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session maker
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session = SessionLocal()
    
    yield session
    
    await session.close()
    await engine.dispose()


@pytest.fixture
async def test_data(test_session):
    """Create test data: teacher, students, lessons"""
    teacher = Teacher(id=1, name="Test Teacher", telegram_id=111, login="teacher1")
    student1 = Student(id=1, name="Student One", teacher_id=1, telegram_id=222)
    student2 = Student(id=2, name="Student Two", teacher_id=1, telegram_id=333)
    
    lesson1 = Lesson(
        id=1,
        date=date.today(),
        time=time(15, 0),
        teacher_id=1,
        student_id=1
    )
    lesson2 = Lesson(
        id=2,
        date=date.today() - timedelta(days=1),
        time=time(14, 0),
        teacher_id=1,
        student_id=2
    )
    
    test_session.add_all([teacher, student1, student2, lesson1, lesson2])
    await test_session.commit()
    
    return {
        'teacher': teacher,
        'student1': student1,
        'student2': student2,
        'lesson1': lesson1,
        'lesson2': lesson2
    }


@pytest.mark.asyncio
async def test_create_homework(test_session, test_data):
    """Test creating homework linked to a lesson"""
    homework_text = "Complete exercises 1-5 from chapter 3"
    
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text=homework_text,
        lesson_id=test_data['lesson1'].id
    )
    
    assert homework.id is not None
    assert homework.student_id == 1
    assert homework.teacher_id == 1
    assert homework.text == homework_text
    assert homework.lesson_id == test_data['lesson1'].id
    assert homework.status == 'sent'
    assert homework.sent_at is not None


@pytest.mark.asyncio
async def test_create_independent_homework(test_session, test_data):
    """Test creating homework not linked to a lesson"""
    homework_text = "Independent study: Read chapters 1-2"
    
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student2'].id,
        teacher_id=test_data['teacher'].id,
        text=homework_text,
        lesson_id=None  # Independent homework
    )
    
    assert homework.lesson_id is None
    assert homework.status == 'sent'


@pytest.mark.asyncio
async def test_create_homework_invalid_student(test_session, test_data):
    """Test creating homework with invalid student"""
    with pytest.raises(ValueError):
        await HomeworkService.create_homework(
            test_session,
            student_id=999,  # Non-existent
            teacher_id=test_data['teacher'].id,
            text="Some homework"
        )


@pytest.mark.asyncio
async def test_update_homework(test_session, test_data):
    """Test updating homework text"""
    # Create homework first
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text="Original homework"
    )
    
    await test_session.commit()
    
    # Update it
    new_text = "Updated homework text"
    updated = await HomeworkService.update_homework(
        test_session,
        homework_id=homework.id,
        teacher_id=test_data['teacher'].id,
        text=new_text
    )
    
    assert updated.text == new_text
    assert updated.edited_at is not None


@pytest.mark.asyncio
async def test_update_homework_wrong_teacher(test_session, test_data):
    """Test that only the teacher who created can edit"""
    # Create homework
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text="Original"
    )
    
    await test_session.commit()
    
    # Try to update with wrong teacher
    with pytest.raises(ValueError, match="doesn't belong to teacher"):
        await HomeworkService.update_homework(
            test_session,
            homework_id=homework.id,
            teacher_id=999,  # Wrong teacher
            text="Malicious edit"
        )


@pytest.mark.asyncio
async def test_mark_homework_received(test_session, test_data):
    """Test marking homework as received"""
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text="Homework"
    )
    
    await test_session.commit()
    
    updated = await HomeworkService.mark_homework_received(
        test_session,
        homework_id=homework.id,
        student_id=test_data['student1'].id
    )
    
    assert updated.status == 'received'
    assert updated.received_at is not None


@pytest.mark.asyncio
async def test_mark_homework_completed(test_session, test_data):
    """Test marking homework as completed"""
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text="Homework"
    )
    
    await test_session.commit()
    
    # Mark as received first
    await HomeworkService.mark_homework_received(
        test_session,
        homework_id=homework.id,
        student_id=test_data['student1'].id
    )
    
    # Then mark as completed
    updated = await HomeworkService.mark_homework_completed(
        test_session,
        homework_id=homework.id,
        student_id=test_data['student1'].id
    )
    
    assert updated.status == 'completed'
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_get_student_homeworks(test_session, test_data):
    """Test retrieving student's homework history"""
    # Create multiple homeworks
    for i in range(3):
        await HomeworkService.create_homework(
            test_session,
            student_id=test_data['student1'].id,
            teacher_id=test_data['teacher'].id,
            text=f"Homework {i}"
        )
    
    await test_session.commit()
    
    homeworks = await HomeworkService.get_student_homeworks(
        test_session,
        student_id=test_data['student1'].id
    )
    
    assert len(homeworks) == 3
    # Should be ordered by sent_at DESC (most recent first)
    assert homeworks[0].sent_at >= homeworks[1].sent_at


@pytest.mark.asyncio
async def test_get_lesson_homework(test_session, test_data):
    """Test retrieving homework for a lesson"""
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text="Lesson homework",
        lesson_id=test_data['lesson1'].id
    )
    
    await test_session.commit()
    
    retrieved = await HomeworkService.get_lesson_homework(
        test_session,
        lesson_id=test_data['lesson1'].id
    )
    
    assert retrieved.id == homework.id


@pytest.mark.asyncio
async def test_delete_homework(test_session, test_data):
    """Test deleting homework"""
    homework = await HomeworkService.create_homework(
        test_session,
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text="To be deleted"
    )
    
    await test_session.commit()
    
    result = await HomeworkService.delete_homework(
        test_session,
        homework_id=homework.id,
        teacher_id=test_data['teacher'].id
    )
    
    assert result is True
    
    # Verify it's deleted
    deleted = await test_session.get(Homework, homework.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_cleanup_old_homework(test_session, test_data):
    """Test cleanup of old homework records"""
    # Create some old homework
    old_date = datetime.utcnow() - timedelta(days=40)
    
    # Create completed homework older than 30 days
    homework_old = Homework(
        student_id=test_data['student1'].id,
        teacher_id=test_data['teacher'].id,
        text="Old completed homework",
        sent_at=old_date,
        status='completed',
        completed_at=old_date + timedelta(hours=1)
    )
    
    # Create recent homework that should NOT be deleted
    homework_recent = Homework(
        student_id=test_data['student2'].id,
        teacher_id=test_data['teacher'].id,
        text="Recent homework",
        sent_at=datetime.utcnow(),
        status='sent'
    )
    
    test_session.add_all([homework_old, homework_recent])
    await test_session.commit()
    
    # Run cleanup with 30-day retention
    deleted_count = await HomeworkService.cleanup_old_homework(
        test_session,
        days=30
    )
    
    assert deleted_count >= 1  # Old homework was deleted
    
    # Verify old homework is gone
    remaining_old = await test_session.get(Homework, homework_old.id)
    assert remaining_old is None
    
    # Verify recent homework still exists
    remaining_recent = await test_session.get(Homework, homework_recent.id)
    assert remaining_recent is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
