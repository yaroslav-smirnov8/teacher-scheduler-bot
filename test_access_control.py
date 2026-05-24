"""Tests for AccessControlService"""
import pytest
import pytest_asyncio
from datetime import date, time
from hypothesis import given, strategies as st, settings, assume
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import Base, Teacher, Student, Lesson, RecurringPattern
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
async def lesson(session, teacher, student):
    """Create test lesson"""
    lesson = Lesson(
        date=date(2024, 6, 15),
        time=time(15, 0),
        teacher_id=teacher.id,
        student_id=student.id
    )
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    return lesson


@pytest_asyncio.fixture
async def recurring_pattern(session, teacher, student):
    """Create test recurring pattern"""
    pattern = RecurringPattern(
        teacher_id=teacher.id,
        student_id=student.id,
        start_date=date(2024, 6, 1),
        end_date=date(2024, 12, 31),
        time=time(15, 0),
        frequency='weekly',
        interval=1,
        weekday=0
    )
    session.add(pattern)
    await session.commit()
    await session.refresh(pattern)
    return pattern


class TestAccessControlPropertyTests:
    """Property 3: Access Control Invariant - a teacher can delete a lesson only if lesson.teacher_id = teacher_id
    
    **Validates: Correctness Property 2**
    """
    
    @pytest.mark.asyncio
    @given(
        teacher_id=st.integers(min_value=1, max_value=100),
        lesson_teacher_id=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=50, deadline=None)
    async def test_access_control_invariant_lesson(self, teacher_id, lesson_teacher_id):
        """Property: Teacher can only access lesson if teacher_id matches lesson.teacher_id"""
        # Create in-memory database for this test
        engine = create_async_engine(TEST_DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        session = SessionLocal()
        
        try:
            # Create teachers with unique telegram_ids and logins
            teacher1 = Teacher(
                name=f"Teacher {teacher_id}",
                contact_info=f"teacher{teacher_id}@example.com",
                login=f"teacher{teacher_id}_a",  # Add suffix to ensure uniqueness
                telegram_id=teacher_id * 10000 + 1000000  # Ensure uniqueness
            )
            session.add(teacher1)
            await session.commit()
            await session.refresh(teacher1)
            
            # Only create teacher2 if different from teacher1
            if teacher_id != lesson_teacher_id:
                teacher2 = Teacher(
                    name=f"Teacher {lesson_teacher_id}",
                    contact_info=f"teacher{lesson_teacher_id}@example.com",
                    login=f"teacher{lesson_teacher_id}_b",  # Add suffix to ensure uniqueness
                    telegram_id=lesson_teacher_id * 10000 + 2000000  # Ensure uniqueness
                )
                session.add(teacher2)
                await session.commit()
                await session.refresh(teacher2)
            else:
                teacher2 = teacher1
            
            # Create student
            student = Student(
                name="Test Student",
                contact_info="student@example.com",
                teacher_id=teacher2.id,
                telegram_id=999999
            )
            session.add(student)
            await session.commit()
            await session.refresh(student)
            
            # Create lesson owned by teacher2
            lesson = Lesson(
                date=date(2024, 6, 15),
                time=time(15, 0),
                teacher_id=teacher2.id,
                student_id=student.id
            )
            session.add(lesson)
            await session.commit()
            await session.refresh(lesson)
            
            # Test access control
            can_access, error = await AccessControlService.verify_teacher_owns_lesson(
                session, teacher1.id, lesson.id
            )
            
            # Property: Access granted if and only if teacher_id matches lesson.teacher_id
            expected_access = (teacher1.id == lesson.teacher_id)
            assert can_access == expected_access, \
                f"Access control failed: teacher_id={teacher1.id}, lesson.teacher_id={lesson.teacher_id}, " \
                f"can_access={can_access}, expected={expected_access}"
            
            if not can_access:
                assert error != "", "Error message should be provided when access is denied"
            else:
                assert error == "", "Error message should be empty when access is granted"
        
        finally:
            await session.close()
            await engine.dispose()
    
    @pytest.mark.asyncio
    @given(
        teacher_id=st.integers(min_value=1, max_value=100),
        pattern_teacher_id=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=50, deadline=None)
    async def test_access_control_invariant_pattern(self, teacher_id, pattern_teacher_id):
        """Property: Teacher can only access pattern if teacher_id matches pattern.teacher_id"""
        # Create in-memory database for this test
        engine = create_async_engine(TEST_DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        session = SessionLocal()
        
        try:
            # Create teachers with unique telegram_ids and logins
            teacher1 = Teacher(
                name=f"Teacher {teacher_id}",
                contact_info=f"teacher{teacher_id}@example.com",
                login=f"teacher{teacher_id}_a",  # Add suffix to ensure uniqueness
                telegram_id=teacher_id * 10000 + 3000000  # Ensure uniqueness
            )
            session.add(teacher1)
            await session.commit()
            await session.refresh(teacher1)
            
            # Only create teacher2 if different from teacher1
            if teacher_id != pattern_teacher_id:
                teacher2 = Teacher(
                    name=f"Teacher {pattern_teacher_id}",
                    contact_info=f"teacher{pattern_teacher_id}@example.com",
                    login=f"teacher{pattern_teacher_id}_b",  # Add suffix to ensure uniqueness
                    telegram_id=pattern_teacher_id * 10000 + 4000000  # Ensure uniqueness
                )
                session.add(teacher2)
                await session.commit()
                await session.refresh(teacher2)
            else:
                teacher2 = teacher1
            
            # Create student
            student = Student(
                name="Test Student",
                contact_info="student@example.com",
                teacher_id=teacher2.id,
                telegram_id=999999
            )
            session.add(student)
            await session.commit()
            await session.refresh(student)
            
            # Create pattern owned by teacher2
            pattern = RecurringPattern(
                teacher_id=teacher2.id,
                student_id=student.id,
                start_date=date(2024, 6, 1),
                end_date=date(2024, 12, 31),
                time=time(15, 0),
                frequency='weekly',
                interval=1,
                weekday=0
            )
            session.add(pattern)
            await session.commit()
            await session.refresh(pattern)
            
            # Test access control
            can_access, error = await AccessControlService.verify_teacher_owns_pattern(
                session, teacher1.id, pattern.id
            )
            
            # Property: Access granted if and only if teacher_id matches pattern.teacher_id
            expected_access = (teacher1.id == pattern.teacher_id)
            assert can_access == expected_access, \
                f"Access control failed: teacher_id={teacher1.id}, pattern.teacher_id={pattern.teacher_id}, " \
                f"can_access={can_access}, expected={expected_access}"
            
            if not can_access:
                assert error != "", "Error message should be provided when access is denied"
            else:
                assert error == "", "Error message should be empty when access is granted"
        
        finally:
            await session.close()
            await engine.dispose()


class TestAccessControlLessonOwnership:
    """Unit tests for lesson ownership verification"""
    
    @pytest.mark.asyncio
    async def test_teacher_owns_lesson_success(self, session, teacher, student, lesson):
        """Test successful verification when teacher owns the lesson"""
        can_access, error = await AccessControlService.verify_teacher_owns_lesson(
            session, teacher.id, lesson.id
        )
        
        assert can_access is True
        assert error == ""
    
    @pytest.mark.asyncio
    async def test_teacher_does_not_own_lesson(self, session, teacher, another_teacher, student, lesson):
        """Test access denial when teacher doesn't own the lesson"""
        can_access, error = await AccessControlService.verify_teacher_owns_lesson(
            session, another_teacher.id, lesson.id
        )
        
        assert can_access is False
        assert "Access denied" in error
        assert "only the lesson's teacher" in error
    
    @pytest.mark.asyncio
    async def test_lesson_not_found(self, session, teacher):
        """Test error when lesson doesn't exist"""
        non_existent_lesson_id = 99999
        can_access, error = await AccessControlService.verify_teacher_owns_lesson(
            session, teacher.id, non_existent_lesson_id
        )
        
        assert can_access is False
        assert "Lesson not found" in error
    
    @pytest.mark.asyncio
    async def test_invalid_teacher_id(self, session, lesson):
        """Test access denial with invalid teacher ID"""
        invalid_teacher_id = 99999
        can_access, error = await AccessControlService.verify_teacher_owns_lesson(
            session, invalid_teacher_id, lesson.id
        )
        
        assert can_access is False
        assert error != ""


class TestAccessControlPatternOwnership:
    """Unit tests for pattern ownership verification"""
    
    @pytest.mark.asyncio
    async def test_teacher_owns_pattern_success(self, session, teacher, student, recurring_pattern):
        """Test successful verification when teacher owns the pattern"""
        can_access, error = await AccessControlService.verify_teacher_owns_pattern(
            session, teacher.id, recurring_pattern.id
        )
        
        assert can_access is True
        assert error == ""
    
    @pytest.mark.asyncio
    async def test_teacher_does_not_own_pattern(self, session, teacher, another_teacher, student, recurring_pattern):
        """Test access denial when teacher doesn't own the pattern"""
        can_access, error = await AccessControlService.verify_teacher_owns_pattern(
            session, another_teacher.id, recurring_pattern.id
        )
        
        assert can_access is False
        assert "Access denied" in error
        assert "only the pattern's teacher" in error
    
    @pytest.mark.asyncio
    async def test_pattern_not_found(self, session, teacher):
        """Test error when pattern doesn't exist"""
        non_existent_pattern_id = 99999
        can_access, error = await AccessControlService.verify_teacher_owns_pattern(
            session, teacher.id, non_existent_pattern_id
        )
        
        assert can_access is False
        assert "Recurring pattern not found" in error
    
    @pytest.mark.asyncio
    async def test_invalid_teacher_id_for_pattern(self, session, recurring_pattern):
        """Test access denial with invalid teacher ID for pattern"""
        invalid_teacher_id = 99999
        can_access, error = await AccessControlService.verify_teacher_owns_pattern(
            session, invalid_teacher_id, recurring_pattern.id
        )
        
        assert can_access is False
        assert error != ""


class TestAccessControlEdgeCases:
    """Edge case tests for access control"""
    
    @pytest.mark.asyncio
    async def test_multiple_lessons_same_teacher(self, session, teacher, student):
        """Test that teacher can access all their lessons"""
        # Create multiple lessons
        lessons = []
        for i in range(3):
            lesson = Lesson(
                date=date(2024, 6, 15 + i),
                time=time(15, 0),
                teacher_id=teacher.id,
                student_id=student.id
            )
            session.add(lesson)
            lessons.append(lesson)
        
        await session.commit()
        
        # Verify teacher can access all lessons
        for lesson in lessons:
            await session.refresh(lesson)
            can_access, error = await AccessControlService.verify_teacher_owns_lesson(
                session, teacher.id, lesson.id
            )
            assert can_access is True
            assert error == ""
    
    @pytest.mark.asyncio
    async def test_multiple_patterns_same_teacher(self, session, teacher, student):
        """Test that teacher can access all their patterns"""
        # Create multiple patterns
        patterns = []
        for i in range(3):
            pattern = RecurringPattern(
                teacher_id=teacher.id,
                student_id=student.id,
                start_date=date(2024, 6, 1 + i),
                end_date=date(2024, 12, 31),
                time=time(15 + i, 0),
                frequency='weekly',
                interval=1,
                weekday=i
            )
            session.add(pattern)
            patterns.append(pattern)
        
        await session.commit()
        
        # Verify teacher can access all patterns
        for pattern in patterns:
            await session.refresh(pattern)
            can_access, error = await AccessControlService.verify_teacher_owns_pattern(
                session, teacher.id, pattern.id
            )
            assert can_access is True
            assert error == ""
    
    @pytest.mark.asyncio
    async def test_lesson_with_pattern_ownership(self, session, teacher, student):
        """Test ownership verification for lesson that's part of a recurring pattern"""
        # Create pattern
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        await session.commit()
        await session.refresh(pattern)
        
        # Create lesson linked to pattern
        lesson = Lesson(
            date=date(2024, 6, 15),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id,
            recurring_pattern_id=pattern.id
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        
        # Verify teacher can access both lesson and pattern
        can_access_lesson, error_lesson = await AccessControlService.verify_teacher_owns_lesson(
            session, teacher.id, lesson.id
        )
        can_access_pattern, error_pattern = await AccessControlService.verify_teacher_owns_pattern(
            session, teacher.id, pattern.id
        )
        
        assert can_access_lesson is True
        assert error_lesson == ""
        assert can_access_pattern is True
        assert error_pattern == ""
