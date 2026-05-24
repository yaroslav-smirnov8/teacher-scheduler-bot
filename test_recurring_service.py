"""Tests for RecurringLessonService"""
import pytest
import pytest_asyncio
from datetime import date, time, timedelta
from hypothesis import given, strategies as st, settings, assume
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import Base, Teacher, Student, Lesson, RecurringPattern, RecurringException
from services.recurring_service import RecurringLessonService
from services.lesson_service import LessonService
from access_control import AccessControlService


# Test database setup
TEST_DB_URL = 'sqlite+aiosqlite:///:memory:'


@pytest_asyncio.fixture
async def engine():
    """Create test database engine"""
    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Create test database session"""
    TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    test_session = TestSessionLocal()
    yield test_session
    await test_session.rollback()
    await test_session.close()


@pytest_asyncio.fixture
async def teacher(session):
    """Create test teacher"""
    teacher = Teacher(
        name="Test Teacher",
        contact_info="test@example.com",
        login="teacher1",
        telegram_id=123456789
    )
    session.add(teacher)
    await session.commit()
    await session.refresh(teacher)
    return teacher


@pytest_asyncio.fixture
async def another_teacher(session):
    """Create another test teacher"""
    teacher = Teacher(
        name="Another Teacher",
        contact_info="another@example.com",
        login="teacher2",
        telegram_id=987654321
    )
    session.add(teacher)
    await session.commit()
    await session.refresh(teacher)
    return teacher


@pytest_asyncio.fixture
async def student(session, teacher):
    """Create test student"""
    student = Student(
        name="Test Student",
        contact_info="student@example.com",
        teacher_id=teacher.id,
        telegram_id=111222333
    )
    session.add(student)
    await session.commit()
    await session.refresh(student)
    return student


@pytest_asyncio.fixture
async def another_student(session, teacher):
    """Create another test student"""
    student = Student(
        name="Another Student",
        contact_info="student2@example.com",
        teacher_id=teacher.id,
        telegram_id=444555666
    )
    session.add(student)
    await session.commit()
    await session.refresh(student)
    return student


class TestCreateRecurringLesson:
    """Tests for create_recurring_lesson()"""
    
    @pytest.mark.asyncio
    async def test_create_recurring_lesson_valid(self, session, teacher, student):
        """Test creating a recurring lesson with valid data"""
        pattern = RecurringPattern(
            start_date=date(2027, 1, 4),  # Monday
            end_date=date(2027, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, message, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        
        assert success is True
        assert "created successfully" in message
        assert result_pattern is not None
        assert result_pattern.id is not None
        assert result_pattern.teacher_id == teacher.id
        assert result_pattern.student_id == student.id
        assert result_pattern.frequency == 'weekly'
        
        # Verify first lesson was created
        result = await session.execute(
            __import__('sqlalchemy').select(Lesson).filter_by(recurring_pattern_id=result_pattern.id)
        )
        first_lesson = result.scalar_one_or_none()
        assert first_lesson is not None
        assert first_lesson.date == date(2027, 1, 4)
        assert first_lesson.time == time(15, 0)
    
    @pytest.mark.asyncio
    async def test_create_recurring_lesson_past_start_date(self, session, teacher, student):
        """Test that creating a recurring lesson with past start_date fails"""
        pattern = RecurringPattern(
            start_date=date(2020, 1, 1),
            end_date=date(2027, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, message, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        
        assert success is False
        assert "past" in message.lower()
        assert result_pattern is None
    
    @pytest.mark.asyncio
    async def test_create_recurring_lesson_end_before_start(self, session, teacher, student):
        """Test that end_date before start_date fails"""
        pattern = RecurringPattern(
            start_date=date(2027, 6, 1),
            end_date=date(2027, 1, 1),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, message, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        
        assert success is False
        assert "end date" in message.lower()
        assert result_pattern is None
    
    @pytest.mark.asyncio
    async def test_create_recurring_lesson_time_conflict(self, session, teacher, student):
        """Test that creating a recurring lesson with time conflict fails"""
        # Create an existing lesson at the same time
        existing_lesson = Lesson(
            date=date(2027, 1, 4),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add(existing_lesson)
        await session.commit()
        
        # Try to create recurring lesson at same time
        pattern = RecurringPattern(
            start_date=date(2027, 1, 4),
            end_date=date(2027, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, message, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        
        assert success is False
        assert result_pattern is None
    
    @pytest.mark.asyncio
    async def test_create_recurring_lesson_biweekly(self, session, teacher, student):
        """Test creating a biweekly recurring lesson"""
        pattern = RecurringPattern(
            start_date=date(2027, 1, 4),
            end_date=date(2027, 3, 31),
            time=time(10, 0),
            frequency='biweekly',
            interval=1,
            weekday=0
        )
        
        success, message, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        
        assert success is True
        assert result_pattern.frequency == 'biweekly'
    
    @pytest.mark.asyncio
    async def test_create_recurring_lesson_monthly(self, session, teacher, student):
        """Test creating a monthly recurring lesson"""
        pattern = RecurringPattern(
            start_date=date(2027, 1, 15),
            end_date=date(2027, 12, 31),
            time=time(14, 0),
            frequency='monthly',
            interval=1,
            day_of_month=15
        )
        
        success, message, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        
        assert success is True
        assert result_pattern.frequency == 'monthly'
        assert result_pattern.day_of_month == 15


class TestConvertToRecurring:
    """Tests for convert_to_recurring()"""
    
    @pytest.mark.asyncio
    async def test_convert_single_lesson(self, session, teacher, student):
        """Test converting a single lesson to recurring"""
        # Create a single lesson
        lesson = Lesson(
            date=date(2027, 1, 4),  # Monday
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        
        # Convert to recurring
        pattern_config = {
            'frequency': 'weekly',
            'interval': 1,
            'end_date': date(2027, 6, 30)
        }
        
        success, message, pattern = await RecurringLessonService.convert_to_recurring(
            session, lesson.id, pattern_config
        )
        
        assert success is True
        assert "converted" in message.lower()
        assert pattern is not None
        assert pattern.teacher_id == teacher.id
        assert pattern.student_id == student.id
        assert pattern.start_date == lesson.date
        assert pattern.time == lesson.time
        assert pattern.weekday == lesson.date.weekday()  # Monday = 0
        assert pattern.created_from_lesson_id == lesson.id
        
        # Verify lesson is now linked to pattern
        await session.refresh(lesson)
        assert lesson.recurring_pattern_id == pattern.id
    
    @pytest.mark.asyncio
    async def test_convert_already_recurring_lesson(self, session, teacher, student):
        """Test that converting an already recurring lesson fails"""
        # Create a pattern and lesson linked to it
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        lesson = Lesson(
            date=date(2027, 1, 4),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        
        # Try to convert already recurring lesson
        pattern_config = {
            'frequency': 'weekly',
            'interval': 1,
            'end_date': date(2027, 12, 31)
        }
        
        success, message, result_pattern = await RecurringLessonService.convert_to_recurring(
            session, lesson.id, pattern_config
        )
        
        assert success is False
        assert "already" in message.lower()
        assert result_pattern is None
    
    @pytest.mark.asyncio
    async def test_convert_nonexistent_lesson(self, session, teacher, student):
        """Test that converting a nonexistent lesson fails"""
        pattern_config = {
            'frequency': 'weekly',
            'interval': 1,
            'end_date': date(2027, 12, 31)
        }
        
        success, message, result_pattern = await RecurringLessonService.convert_to_recurring(
            session, 99999, pattern_config
        )
        
        assert success is False
        assert "not found" in message.lower()
        assert result_pattern is None
    
    @pytest.mark.asyncio
    async def test_convert_monthly_from_lesson(self, session, teacher, student):
        """Test converting a lesson to monthly recurring"""
        lesson = Lesson(
            date=date(2027, 1, 15),
            time=time(14, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        
        pattern_config = {
            'frequency': 'monthly',
            'interval': 1,
            'end_date': date(2027, 12, 31)
        }
        
        success, message, pattern = await RecurringLessonService.convert_to_recurring(
            session, lesson.id, pattern_config
        )
        
        assert success is True
        assert pattern.frequency == 'monthly'
        assert pattern.day_of_month == 15  # day of month from lesson date


class TestDeleteSingleInstance:
    """Tests for delete_single_instance()"""
    
    @pytest.mark.asyncio
    async def test_delete_single_recurring_instance(self, session, teacher, student):
        """Test deleting a single instance of a recurring lesson creates exception"""
        # Create pattern and lesson
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        lesson = Lesson(
            date=date(2027, 1, 4),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        
        # Delete single instance
        success, message = await RecurringLessonService.delete_single_instance(
            session, lesson.id, lesson.date
        )
        
        assert success is True
        assert "deleted" in message.lower()
        
        # Verify exception was created
        result = await session.execute(
            __import__('sqlalchemy').select(RecurringException).filter_by(
                pattern_id=pattern.id,
                exception_date=lesson.date
            )
        )
        exception = result.scalar_one_or_none()
        assert exception is not None
        assert exception.reason == "Deleted by teacher"
        
        # Verify lesson was deleted
        result = await session.execute(
            __import__('sqlalchemy').select(Lesson).filter_by(id=lesson.id)
        )
        assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_delete_single_non_recurring_instance(self, session, teacher, student):
        """Test deleting a single non-recurring lesson (no exception created)"""
        lesson = Lesson(
            date=date(2027, 1, 4),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        lesson_id = lesson.id
        
        # Delete single instance
        success, message = await RecurringLessonService.delete_single_instance(
            session, lesson.id, lesson.date
        )
        
        assert success is True
        
        # Verify no exception was created (lesson is not recurring)
        result = await session.execute(
            __import__('sqlalchemy').select(RecurringException)
        )
        assert result.scalar_one_or_none() is None
        
        # Verify lesson was deleted
        result = await session.execute(
            __import__('sqlalchemy').select(Lesson).filter_by(id=lesson_id)
        )
        assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_lesson(self, session, teacher, student):
        """Test that deleting a nonexistent lesson fails"""
        success, message = await RecurringLessonService.delete_single_instance(
            session, 99999, date(2027, 1, 4)
        )
        
        assert success is False
        assert "not found" in message.lower()
    
    @pytest.mark.asyncio
    async def test_delete_single_instance_idempotent(self, session, teacher, student):
        """Test that deleting same instance twice is handled gracefully"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        lesson = Lesson(
            date=date(2027, 1, 4),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        
        # First delete
        success1, _ = await RecurringLessonService.delete_single_instance(
            session, lesson.id, lesson.date
        )
        assert success1 is True
        
        # Second delete (lesson no longer exists)
        success2, message2 = await RecurringLessonService.delete_single_instance(
            session, lesson.id, lesson.date
        )
        assert success2 is False
        assert "not found" in message2.lower()


class TestDeleteRecurringSeries:
    """Tests for delete_recurring_series()"""
    
    @pytest.mark.asyncio
    async def test_delete_series(self, session, teacher, student):
        """Test deleting an entire recurring series"""
        # Create pattern
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        # Create multiple future lessons
        lesson1 = Lesson(
            date=date(2027, 1, 4),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        lesson2 = Lesson(
            date=date(2027, 1, 11),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        session.add_all([lesson1, lesson2])
        await session.commit()
        
        # Delete series
        success, message = await RecurringLessonService.delete_recurring_series(
            session, pattern.id
        )
        
        assert success is True
        assert "deleted" in message.lower()
        
        # Verify pattern is deleted
        result = await session.execute(
            __import__('sqlalchemy').select(RecurringPattern).filter_by(id=pattern.id)
        )
        assert result.scalar_one_or_none() is None
        
        # Verify lessons are deleted
        result = await session.execute(
            __import__('sqlalchemy').select(Lesson).filter_by(recurring_pattern_id=pattern.id)
        )
        assert result.scalars().all() == []
    
    @pytest.mark.asyncio
    async def test_delete_series_preserves_past_lessons(self, session, teacher, student):
        """Test that deleting series preserves past lessons for history"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2020, 1, 6),
            end_date=date(2030, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        # Create a past lesson
        past_lesson = Lesson(
            date=date(2020, 1, 6),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        session.add(past_lesson)
        await session.commit()
        past_lesson_id = past_lesson.id
        
        # Delete series
        success, message = await RecurringLessonService.delete_recurring_series(
            session, pattern.id
        )
        
        assert success is True
        
        # Past lesson should be deleted too (since we delete all lessons with pattern_id >= today)
        # Actually, the past lesson has date < today, so it should be preserved
        result = await session.execute(
            __import__('sqlalchemy').select(Lesson).filter_by(id=past_lesson_id)
        )
        # Past lesson should be preserved (date < today)
        preserved = result.scalar_one_or_none()
        assert preserved is not None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_series(self, session, teacher, student):
        """Test that deleting a nonexistent series fails"""
        success, message = await RecurringLessonService.delete_recurring_series(
            session, 99999
        )
        
        assert success is False
        assert "not found" in message.lower()
    
    @pytest.mark.asyncio
    async def test_delete_series_cascades_exceptions(self, session, teacher, student):
        """Test that deleting series cascades to exceptions"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        # Create an exception
        exception = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2027, 1, 11),
            reason="Holiday"
        )
        session.add(exception)
        await session.commit()
        
        # Delete series
        success, message = await RecurringLessonService.delete_recurring_series(
            session, pattern.id
        )
        
        assert success is True
        
        # Verify exceptions are cascade deleted
        result = await session.execute(
            __import__('sqlalchemy').select(RecurringException).filter_by(pattern_id=pattern.id)
        )
        assert result.scalars().all() == []


class TestGetRecurringLessons:
    """Tests for get_recurring_lessons()"""
    
    @pytest.mark.asyncio
    async def test_get_recurring_lessons_returns_correct_dates(self, session, teacher, student):
        """Test that get_recurring_lessons returns correct dates for a pattern"""
        # Create a weekly pattern
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),  # Monday
            end_date=date(2027, 1, 27),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.commit()
        
        # Get lessons for the range
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        # Should have 4 Mondays in January 2027: 4, 11, 18, 25
        recurring_dates = [l.date for l in lessons if l.recurring_pattern_id == pattern.id]
        expected_dates = [date(2027, 1, 4), date(2027, 1, 11), date(2027, 1, 18), date(2027, 1, 25)]
        assert recurring_dates == expected_dates
    
    @pytest.mark.asyncio
    async def test_get_recurring_lessons_excludes_exceptions(self, session, teacher, student):
        """Test that excluded dates are not in the results"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 1, 27),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        # Create exception for Jan 13
        exception = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2027, 1, 11),
            reason="Holiday"
        )
        session.add(exception)
        await session.commit()
        
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        # Should not include Jan 11
        lesson_dates = [l.date for l in lessons]
        assert date(2027, 1, 11) not in lesson_dates
        assert date(2027, 1, 4) in lesson_dates
        assert date(2027, 1, 18) in lesson_dates
        assert date(2027, 1, 25) in lesson_dates
    
    @pytest.mark.asyncio
    async def test_get_recurring_lessons_includes_one_time(self, session, teacher, student):
        """Test that one-time lessons are included in results"""
        # Create a one-time lesson
        one_time = Lesson(
            date=date(2027, 1, 10),
            time=time(10, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add(one_time)
        await session.commit()
        
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        # Should include the one-time lesson
        one_time_lessons = [l for l in lessons if l.recurring_pattern_id is None]
        assert len(one_time_lessons) == 1
        assert one_time_lessons[0].date == date(2027, 1, 10)
    
    @pytest.mark.asyncio
    async def test_get_recurring_lessons_sorted(self, session, teacher, student):
        """Test that lessons are sorted by (date, time)"""
        # Create lessons at different times
        lesson1 = Lesson(
            date=date(2027, 1, 10),
            time=time(14, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        lesson2 = Lesson(
            date=date(2027, 1, 10),
            time=time(10, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        lesson3 = Lesson(
            date=date(2027, 1, 5),
            time=time(12, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add_all([lesson1, lesson2, lesson3])
        await session.commit()
        
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        # Verify sorted order
        for i in range(len(lessons) - 1):
            assert (lessons[i].date, lessons[i].time) <= (lessons[i+1].date, lessons[i+1].time)
    
    @pytest.mark.asyncio
    async def test_get_recurring_lessons_by_student(self, session, teacher, student, another_student):
        """Test filtering by student_id"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 1, 27),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.commit()
        
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, student_id=student.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        assert len(lessons) > 0
        for lesson in lessons:
            assert lesson.student_id == student.id
    
    @pytest.mark.asyncio
    async def test_get_recurring_lessons_no_ids(self, session):
        """Test that no teacher_id or student_id returns empty list"""
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        assert lessons == []
    
    @pytest.mark.asyncio
    async def test_get_recurring_lessons_uses_existing_db_lessons(self, session, teacher, student):
        """Test that existing DB lessons are used instead of generating new ones"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 1, 27),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.flush()
        
        # Create a real lesson for Jan 4
        real_lesson = Lesson(
            date=date(2027, 1, 4),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        session.add(real_lesson)
        await session.commit()
        
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        # The real lesson should be in the results
        db_lessons = [l for l in lessons if l.id is not None and l.date == date(2027, 1, 4)]
        assert len(db_lessons) == 1


class TestRecurringLessonPropertyTests:
    """Property-based tests for RecurringLessonService
    
    Property 4: Memory Efficiency - memory usage is proportional to
    the size of the time window, not all future lessons
    """
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_small_window(self, session, teacher, student):
        """Property: Generating a small window produces fewer lessons than a large window"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2027, 1, 4),
            end_date=date(2027, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.commit()
        
        # Small window (1 week)
        small_lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 7)
        )
        
        # Large window (1 year)
        large_lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 12, 31)
        )
        
        # Small window should produce fewer lessons
        assert len(small_lessons) < len(large_lessons)
        
        # Small window should have at most 1 lesson (1 Monday in that week)
        assert len(small_lessons) <= 2
    
    @pytest.mark.asyncio
    @given(
        window_days=st.integers(min_value=7, max_value=365)
    )
    @settings(max_examples=20, deadline=None)
    async def test_lessons_within_requested_window(self, window_days):
        """Property: All generated lessons fall within the requested time window"""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        session = SessionLocal()
        
        try:
            teacher = Teacher(
                name="Prop Teacher",
                contact_info="prop@example.com",
                login="prop_teacher",
                telegram_id=777777
            )
            session.add(teacher)
            await session.commit()
            await session.refresh(teacher)
            
            student = Student(
                name="Prop Student",
                contact_info="prop_student@example.com",
                teacher_id=teacher.id,
                telegram_id=888888
            )
            session.add(student)
            await session.commit()
            await session.refresh(student)
            
            pattern = RecurringPattern(
                teacher_id=teacher.id,
                student_id=student.id,
                start_date=date(2027, 1, 4),
                end_date=date(2027, 12, 31),
                time=time(15, 0),
                frequency='weekly',
                interval=1,
                weekday=0
            )
            session.add(pattern)
            await session.commit()
            
            start = date(2027, 1, 1)
            end = start + timedelta(days=window_days)
            
            lessons = await RecurringLessonService.get_recurring_lessons(
                session, teacher_id=teacher.id,
                start_date=start, end_date=end
            )
            
            for lesson in lessons:
                assert start <= lesson.date <= end, \
                    f"Lesson date {lesson.date} outside window [{start}, {end}]"
        finally:
            await session.close()
            await engine.dispose()
