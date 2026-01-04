"""Pytest configuration and shared fixtures."""

import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock

from models import Base, Teacher, Student, Lesson


@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create database session for testing."""
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def sample_teacher(test_session):
    """Create sample teacher for testing."""
    teacher = Teacher(
        name="John Doe",
        contact_info="john@example.com",
        login="johndoe",
        telegram_id=123456789
    )
    test_session.add(teacher)
    test_session.commit()
    test_session.refresh(teacher)
    return teacher


@pytest.fixture
def sample_student(test_session, sample_teacher):
    """Create sample student for testing."""
    student = Student(
        name="Alice Smith",
        contact_info="alice@example.com",
        teacher_id=sample_teacher.id,
        telegram_id=987654321
    )
    test_session.add(student)
    test_session.commit()
    test_session.refresh(student)
    return student


@pytest.fixture
def sample_lesson(test_session, sample_teacher, sample_student):
    """Create sample lesson for testing."""
    tomorrow = date.today() + timedelta(days=1)
    lesson = Lesson(
        date=tomorrow,
        time=time(15, 0),
        teacher_id=sample_teacher.id,
        student_id=sample_student.id
    )
    test_session.add(lesson)
    test_session.commit()
    test_session.refresh(lesson)
    return lesson


@pytest.fixture
def mock_bot():
    """Mock Telegram bot for testing handlers."""
    bot = Mock()
    bot.send_message = Mock(return_value=True)
    return bot


@pytest.fixture
def mock_update():
    """Mock Telegram update object."""
    update = Mock()
    update.message = Mock()
    update.message.from_user = Mock()
    update.message.from_user.id = 123456789
    update.message.text = "Test message"
    update.callback_query = Mock()
    update.callback_query.from_user = Mock()
    update.callback_query.from_user.id = 123456789
    update.callback_query.data = "test_callback"
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram context object."""
    context = Mock()
    context.user_data = {}
    context.bot = Mock()
    context.bot.send_message = Mock(return_value=True)
    return context
