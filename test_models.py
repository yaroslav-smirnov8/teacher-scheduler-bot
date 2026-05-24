"""Unit tests for RecurringPattern and RecurringException models"""
import pytest
from datetime import date, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from models import Base, Teacher, Student, RecurringPattern, RecurringException, Lesson


# Test database setup
TEST_DB_URL = 'sqlite:///:memory:'


@pytest.fixture
def engine():
    """Create test database engine"""
    test_engine = create_engine(TEST_DB_URL, echo=False)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine):
    """Create test database session"""
    TestSessionLocal = sessionmaker(bind=engine)
    test_session = TestSessionLocal()
    yield test_session
    test_session.rollback()
    test_session.close()


@pytest.fixture
def teacher(session):
    """Create test teacher"""
    teacher = Teacher(
        name="Test Teacher",
        contact_info="test@example.com",
        login="teacher1",
        telegram_id=123456789
    )
    session.add(teacher)
    session.commit()
    session.refresh(teacher)
    return teacher


@pytest.fixture
def student(session, teacher):
    """Create test student"""
    student = Student(
        name="Test Student",
        contact_info="student@example.com",
        teacher_id=teacher.id,
        telegram_id=987654321
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


class TestRecurringPatternCreation:
    """Tests for creating RecurringPattern with valid data"""
    
    def test_create_weekly_pattern(self, session, teacher, student):
        """Test creating a weekly recurring pattern"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 6, 30),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0  # Monday
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        assert pattern.id is not None
        assert pattern.teacher_id == teacher.id
        assert pattern.student_id == student.id
        assert pattern.frequency == 'weekly'
        assert pattern.interval == 1
        assert pattern.weekday == 0
    
    def test_create_biweekly_pattern(self, session, teacher, student):
        """Test creating a biweekly recurring pattern"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 12, 31),
            time=time(14, 30),
            frequency='biweekly',
            interval=1,
            weekday=2  # Wednesday
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        assert pattern.id is not None
        assert pattern.frequency == 'biweekly'
        assert pattern.weekday == 2
    
    def test_create_monthly_pattern(self, session, teacher, student):
        """Test creating a monthly recurring pattern"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 12, 15),
            time=time(16, 0),
            frequency='monthly',
            interval=1,
            day_of_month=15
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        assert pattern.id is not None
        assert pattern.frequency == 'monthly'
        assert pattern.day_of_month == 15
    
    def test_create_pattern_without_end_date(self, session, teacher, student):
        """Test creating a pattern without end date (infinite)"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            end_date=None,
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        assert pattern.id is not None
        assert pattern.end_date is None
    
    def test_create_pattern_with_created_from_lesson(self, session, teacher, student):
        """Test creating a pattern linked to an original lesson"""
        # Create a lesson first
        lesson = Lesson(
            date=date(2024, 1, 8),
            time=time(15, 0),
            teacher_id=teacher.id,
            student_id=student.id
        )
        session.add(lesson)
        session.commit()
        session.refresh(lesson)
        
        # Create pattern from lesson
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0,
            created_from_lesson_id=lesson.id
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        assert pattern.id is not None
        assert pattern.created_from_lesson_id == lesson.id


class TestRecurringPatternFrequencyValidation:
    """Tests for frequency validation"""
    
    def test_valid_frequency_weekly(self, session, teacher, student):
        """Test that 'weekly' frequency is accepted"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        
        assert pattern.frequency == 'weekly'
    
    def test_valid_frequency_biweekly(self, session, teacher, student):
        """Test that 'biweekly' frequency is accepted"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='biweekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        
        assert pattern.frequency == 'biweekly'
    
    def test_valid_frequency_monthly(self, session, teacher, student):
        """Test that 'monthly' frequency is accepted"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 15),
            time=time(15, 0),
            frequency='monthly',
            interval=1,
            day_of_month=15
        )
        session.add(pattern)
        session.commit()
        
        assert pattern.frequency == 'monthly'
    
    def test_invalid_frequency_raises_error(self, session, teacher, student):
        """Test that invalid frequency raises ValueError"""
        with pytest.raises(ValueError, match="Frequency must be one of"):
            pattern = RecurringPattern(
                teacher_id=teacher.id,
                student_id=student.id,
                start_date=date(2024, 1, 8),
                time=time(15, 0),
                frequency='daily',  # Invalid frequency
                interval=1,
                weekday=0
            )
    
    def test_invalid_frequency_yearly(self, session, teacher, student):
        """Test that 'yearly' frequency is rejected"""
        with pytest.raises(ValueError, match="Frequency must be one of"):
            pattern = RecurringPattern(
                teacher_id=teacher.id,
                student_id=student.id,
                start_date=date(2024, 1, 8),
                time=time(15, 0),
                frequency='yearly',
                interval=1,
                weekday=0
            )
    
    def test_empty_frequency_raises_error(self, session, teacher, student):
        """Test that empty frequency raises ValueError"""
        with pytest.raises(ValueError, match="Frequency must be one of"):
            pattern = RecurringPattern(
                teacher_id=teacher.id,
                student_id=student.id,
                start_date=date(2024, 1, 8),
                time=time(15, 0),
                frequency='',
                interval=1,
                weekday=0
            )


class TestRecurringExceptionCascadeDelete:
    """Tests for cascade delete behavior"""
    
    def test_deleting_pattern_deletes_exceptions(self, session, teacher, student):
        """Test that deleting a pattern cascades to delete its exceptions"""
        # Create pattern
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        # Create exceptions
        exception1 = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2024, 1, 15),
            reason="Holiday"
        )
        exception2 = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2024, 1, 22),
            reason="Sick day"
        )
        session.add_all([exception1, exception2])
        session.commit()
        
        # Verify exceptions exist
        exceptions = session.query(RecurringException).filter_by(pattern_id=pattern.id).all()
        assert len(exceptions) == 2
        
        # Delete pattern
        session.delete(pattern)
        session.commit()
        
        # Verify exceptions are deleted
        exceptions = session.query(RecurringException).filter_by(pattern_id=pattern.id).all()
        assert len(exceptions) == 0
    
    def test_deleting_pattern_with_no_exceptions(self, session, teacher, student):
        """Test that deleting a pattern without exceptions works correctly"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        pattern_id = pattern.id
        
        # Delete pattern
        session.delete(pattern)
        session.commit()
        
        # Verify pattern is deleted
        deleted_pattern = session.query(RecurringPattern).filter_by(id=pattern_id).first()
        assert deleted_pattern is None
    
    def test_deleting_pattern_with_multiple_exceptions(self, session, teacher, student):
        """Test cascade delete with multiple exceptions"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        # Create 5 exceptions with valid dates
        exceptions = [
            RecurringException(
                pattern_id=pattern.id,
                exception_date=date(2024, 1, 15),
                reason="Exception 0"
            ),
            RecurringException(
                pattern_id=pattern.id,
                exception_date=date(2024, 1, 22),
                reason="Exception 1"
            ),
            RecurringException(
                pattern_id=pattern.id,
                exception_date=date(2024, 1, 29),
                reason="Exception 2"
            ),
            RecurringException(
                pattern_id=pattern.id,
                exception_date=date(2024, 2, 5),
                reason="Exception 3"
            ),
            RecurringException(
                pattern_id=pattern.id,
                exception_date=date(2024, 2, 12),
                reason="Exception 4"
            )
        ]
        session.add_all(exceptions)
        session.commit()
        
        # Delete pattern
        session.delete(pattern)
        session.commit()
        
        # Verify all exceptions are deleted
        remaining_exceptions = session.query(RecurringException).filter_by(pattern_id=pattern.id).all()
        assert len(remaining_exceptions) == 0


class TestRecurringExceptionUniqueConstraint:
    """Tests for unique constraint on (pattern_id, exception_date)"""
    
    def test_unique_constraint_prevents_duplicate(self, session, teacher, student):
        """Test that duplicate (pattern_id, exception_date) raises IntegrityError"""
        # Create pattern
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        # Create first exception
        exception1 = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2024, 1, 15),
            reason="Holiday"
        )
        session.add(exception1)
        session.commit()
        
        # Try to create duplicate exception
        exception2 = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2024, 1, 15),  # Same date
            reason="Different reason"
        )
        session.add(exception2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_same_date_different_patterns_allowed(self, session, teacher, student):
        """Test that same date is allowed for different patterns"""
        # Create two patterns
        pattern1 = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        pattern2 = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 9),
            time=time(16, 0),
            frequency='weekly',
            interval=1,
            weekday=1
        )
        session.add_all([pattern1, pattern2])
        session.commit()
        session.refresh(pattern1)
        session.refresh(pattern2)
        
        # Create exceptions with same date for different patterns
        exception1 = RecurringException(
            pattern_id=pattern1.id,
            exception_date=date(2024, 1, 15),
            reason="Holiday"
        )
        exception2 = RecurringException(
            pattern_id=pattern2.id,
            exception_date=date(2024, 1, 15),  # Same date, different pattern
            reason="Holiday"
        )
        session.add_all([exception1, exception2])
        session.commit()
        
        # Both should be created successfully
        session.refresh(exception1)
        session.refresh(exception2)
        assert exception1.id is not None
        assert exception2.id is not None
    
    def test_different_dates_same_pattern_allowed(self, session, teacher, student):
        """Test that different dates are allowed for the same pattern"""
        pattern = RecurringPattern(
            teacher_id=teacher.id,
            student_id=student.id,
            start_date=date(2024, 1, 8),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        
        # Create multiple exceptions with different dates
        exception1 = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2024, 1, 15),
            reason="Holiday"
        )
        exception2 = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2024, 1, 22),
            reason="Sick day"
        )
        exception3 = RecurringException(
            pattern_id=pattern.id,
            exception_date=date(2024, 1, 29),
            reason="Vacation"
        )
        session.add_all([exception1, exception2, exception3])
        session.commit()
        
        # All should be created successfully
        exceptions = session.query(RecurringException).filter_by(pattern_id=pattern.id).all()
        assert len(exceptions) == 3
