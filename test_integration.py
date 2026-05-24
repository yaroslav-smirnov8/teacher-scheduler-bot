"""Integration tests for recurring lessons system - end-to-end scenarios"""
import pytest
import pytest_asyncio
from datetime import date, time, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from models import Base, Teacher, Student, Lesson, RecurringPattern, RecurringException
from services.recurring_service import RecurringLessonService
from services.lesson_service import LessonService
from access_control import AccessControlService
from database import init_db


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
        name="Integration Teacher",
        contact_info="int@example.com",
        login="int_teacher",
        telegram_id=555666777
    )
    session.add(teacher)
    await session.commit()
    await session.refresh(teacher)
    return teacher


@pytest_asyncio.fixture
async def student(session, teacher):
    """Create test student"""
    student = Student(
        name="Integration Student",
        contact_info="int_student@example.com",
        teacher_id=teacher.id,
        telegram_id=333444555
    )
    session.add(student)
    await session.commit()
    await session.refresh(student)
    return student


class TestEndToEndRecurringCreation:
    """Integration test: Create recurring lesson -> view schedule -> see all instances"""
    
    @pytest.mark.asyncio
    async def test_create_and_view_recurring_lessons(self, session, teacher, student):
        """End-to-end: Create recurring lesson, then view schedule shows all instances"""
        # Step 1: Create a recurring lesson
        pattern = RecurringPattern(
            start_date=date(2027, 1, 4),  # Monday
            end_date=date(2027, 1, 25),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, message, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        
        assert success is True
        
        # Step 2: View schedule for the period
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        # Step 3: Verify all instances are visible
        assert len(lessons) >= 4  # 4 Mondays: 4, 11, 18, 25
        recurring_lessons = [l for l in lessons if l.recurring_pattern_id == result_pattern.id]
        assert len(recurring_lessons) == 4
        
        # Verify dates
        dates = [l.date for l in recurring_lessons]
        assert date(2027, 1, 4) in dates
        assert date(2027, 1, 11) in dates
        assert date(2027, 1, 18) in dates
        assert date(2027, 1, 25) in dates


class TestEndToEndConvertAndDelete:
    """Integration test: Convert -> Delete series -> all instances removed"""
    
    @pytest.mark.asyncio
    async def test_convert_to_recurring_then_delete_series(self, session, teacher, student):
        """End-to-end: Convert single lesson to recurring, then delete series"""
        # Step 1: Create a single lesson
        lesson = Lesson(
            date=date(2027, 1, 4),  # Monday
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        
        # Step 2: Convert to recurring
        pattern_config = {
            'frequency': 'weekly',
            'interval': 1,
            'end_date': date(2027, 1, 25)
        }
        
        success, message, pattern = await RecurringLessonService.convert_to_recurring(
            session, lesson.id, pattern_config
        )
        
        assert success is True
        
        # Step 3: Verify schedule shows recurring instances
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        recurring_lessons = [l for l in lessons if l.recurring_pattern_id == pattern.id]
        assert len(recurring_lessons) == 4  # 4 Mondays
        
        # Step 4: Delete the series
        success, message = await RecurringLessonService.delete_recurring_series(
            session, pattern.id
        )
        
        assert success is True
        
        # Step 5: Verify all instances are gone
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        assert len(lessons) == 0


class TestEndToEndDeleteSingleInstance:
    """Integration test: Delete single instance -> exception created -> instance not in schedule"""
    
    @pytest.mark.asyncio
    async def test_delete_single_instance_creates_exception(self, session, teacher, student):
        """End-to-end: Delete single instance, verify exception and schedule"""
        # Step 1: Create recurring lesson
        pattern = RecurringPattern(
            start_date=date(2027, 1, 4),
            end_date=date(2027, 1, 25),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, _, pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        assert success is True
        
        # Step 2: Get the first lesson instance
        result = await session.execute(
            select(Lesson).filter(
                Lesson.recurring_pattern_id == pattern.id,
                Lesson.date == date(2027, 1, 4)
            )
        )
        first_lesson = result.scalar_one_or_none()
        assert first_lesson is not None
        
        # Step 3: Delete single instance
        success, message = await RecurringLessonService.delete_single_instance(
            session, first_lesson.id, first_lesson.date
        )
        
        assert success is True
        
        # Step 4: Verify exception was created
        result = await session.execute(
            select(RecurringException).filter_by(
                pattern_id=pattern.id,
                exception_date=date(2027, 1, 4)
            )
        )
        exception = result.scalar_one_or_none()
        assert exception is not None
        
        # Step 5: Verify schedule doesn't include the deleted instance
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        lesson_dates = [l.date for l in lessons]
        assert date(2027, 1, 4) not in lesson_dates  # Deleted
        assert date(2027, 1, 11) in lesson_dates  # Still present
        assert date(2027, 1, 18) in lesson_dates  # Still present
        assert date(2027, 1, 25) in lesson_dates  # Still present


class TestEndToEndMultiplePatterns:
    """Integration test: Multiple patterns with overlapping dates"""
    
    @pytest.mark.asyncio
    async def test_multiple_patterns_overlapping_dates(self, session, teacher, student):
        """Test that multiple recurring patterns work correctly together"""
        # Create a weekly Monday pattern
        pattern1 = RecurringPattern(
            start_date=date(2027, 1, 4),
            end_date=date(2027, 1, 25),
            time=time(10, 0),
            frequency='weekly',
            interval=1,
            weekday=0  # Monday
        )
        
        # Create a weekly Wednesday pattern
        pattern2 = RecurringPattern(
            start_date=date(2027, 1, 6),
            end_date=date(2027, 1, 27),
            time=time(14, 0),
            frequency='weekly',
            interval=1,
            weekday=2  # Wednesday
        )
        
        success1, _, p1 = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern1
        )
        success2, _, p2 = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern2
        )
        
        assert success1 is True
        assert success2 is True
        
        # View schedule
        lessons = await RecurringLessonService.get_recurring_lessons(
            session, teacher_id=teacher.id,
            start_date=date(2027, 1, 1), end_date=date(2027, 1, 31)
        )
        
        # Should have both Monday and Wednesday lessons
        monday_lessons = [l for l in lessons if l.date.weekday() == 0 and l.time == time(10, 0)]
        wednesday_lessons = [l for l in lessons if l.date.weekday() == 2 and l.time == time(14, 0)]
        
        assert len(monday_lessons) == 4  # 4 Mondays
        assert len(wednesday_lessons) == 4  # 4 Wednesdays
        
        # Total should be 8
        assert len(lessons) == 8


class TestEndToEndAccessControl:
    """Integration test: Access control prevents unauthorized deletions"""
    
    @pytest.mark.asyncio
    async def test_teacher_cannot_delete_other_teachers_lesson(self, session, teacher, student):
        """Test that a teacher cannot delete another teacher's recurring lesson"""
        # Create another teacher
        other_teacher = Teacher(
            name="Other Teacher",
            contact_info="other@example.com",
            login="other_teacher_int",
            telegram_id=999888777
        )
        session.add(other_teacher)
        await session.commit()
        await session.refresh(other_teacher)
        
        # Create a recurring lesson owned by the first teacher
        pattern = RecurringPattern(
            start_date=date(2027, 1, 4),
            end_date=date(2027, 1, 25),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, _, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        assert success is True
        
        # Try to access with wrong teacher
        can_access, error = await AccessControlService.verify_teacher_owns_pattern(
            session, other_teacher.id, result_pattern.id
        )
        
        assert can_access is False
        assert "Access denied" in error
        
        # Verify the pattern still exists
        result = await session.execute(
            select(RecurringPattern).filter_by(id=result_pattern.id)
        )
        assert result.scalar_one_or_none() is not None


class TestEndToEndDatabaseMigration:
    """Integration test: Database initialization and migration"""
    
    @pytest.mark.asyncio
    async def test_init_db_creates_all_tables_with_migration(self):
        """Test that init_db creates all tables including recurring ones"""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        
        # Override engine for init_db
        import database
        original_engine = database.engine
        database.engine = engine
        
        try:
            await init_db()
            
            # Verify all tables exist
            async with engine.begin() as conn:
                def get_table_names(connection):
                    from sqlalchemy import inspect
                    inspector = inspect(connection)
                    return inspector.get_table_names()
                
                tables = await conn.run_sync(get_table_names)
            
            assert 'teachers' in tables
            assert 'students' in tables
            assert 'lessons' in tables
            assert 'recurring_patterns' in tables
            assert 'recurring_exceptions' in tables
            assert 'schema_version' in tables
        finally:
            database.engine = original_engine
            await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_init_db_is_idempotent(self):
        """Test that init_db can be called multiple times safely"""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        
        import database
        original_engine = database.engine
        database.engine = engine
        
        try:
            # Call init_db twice
            await init_db()
            await init_db()
            
            # Verify tables still exist
            async with engine.begin() as conn:
                def get_table_names(connection):
                    from sqlalchemy import inspect
                    inspector = inspect(connection)
                    return inspector.get_table_names()
                
                tables = await conn.run_sync(get_table_names)
            
            assert 'recurring_patterns' in tables
            assert 'recurring_exceptions' in tables
        finally:
            database.engine = original_engine
            await engine.dispose()


class TestEndToEndErrorHandling:
    """Integration test: Error handling in critical paths"""
    
    @pytest.mark.asyncio
    async def test_create_recurring_with_invalid_frequency(self, session, teacher, student):
        """Test that invalid frequency is rejected at model level"""
        # Invalid frequency raises ValueError at model creation time
        with pytest.raises(ValueError, match="Frequency must be one of"):
            pattern = RecurringPattern(
                start_date=date(2027, 1, 4),
                end_date=date(2027, 6, 30),
                time=time(15, 0),
                frequency='daily',  # Invalid
                interval=1,
                weekday=0
            )
            # This should raise during creation
            await RecurringLessonService.create_recurring_lesson(
                session, teacher.id, student.id, pattern
            )
    
    @pytest.mark.asyncio
    async def test_convert_nonexistent_lesson_returns_error(self, session, teacher, student):
        """Test that converting a nonexistent lesson returns proper error"""
        pattern_config = {
            'frequency': 'weekly',
            'interval': 1,
            'end_date': date(2027, 12, 31)
        }
        
        success, message, result = await RecurringLessonService.convert_to_recurring(
            session, 99999, pattern_config
        )
        
        assert success is False
        assert "not found" in message.lower()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_series_twice_handled_gracefully(self, session, teacher, student):
        """Test that deleting a series twice returns proper error"""
        pattern = RecurringPattern(
            start_date=date(2027, 1, 4),
            end_date=date(2027, 1, 25),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        success, _, result_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student.id, pattern
        )
        assert success is True
        
        # First delete
        success1, msg1 = await RecurringLessonService.delete_recurring_series(
            session, result_pattern.id
        )
        assert success1 is True
        
        # Second delete
        success2, msg2 = await RecurringLessonService.delete_recurring_series(
            session, result_pattern.id
        )
        assert success2 is False
        assert "not found" in msg2.lower()
