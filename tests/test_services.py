"""Unit tests for service layer business logic."""

import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import Mock, patch

from services import LessonService, NotificationService


@pytest.fixture
def mock_session():
    """Mock database session for unit tests."""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.delete = Mock()
    session.refresh = Mock()
    return session


def test_conflict_detection_teacher_conflict(mock_session):
    """Test conflict detection when teacher has existing lesson."""
    existing_lesson = Mock()
    mock_session.query.return_value.filter.return_value.first.return_value = existing_lesson
    
    is_valid, error_msg = LessonService.check_time_conflict(
        mock_session, teacher_id=1, student_id=2,
        lesson_date=date(2024, 3, 15), lesson_time=time(15, 0)
    )
    
    assert is_valid is False
    assert "teacher already has a lesson" in error_msg


def test_conflict_detection_student_conflict(mock_session):
    """Test conflict detection when student has existing lesson."""
    mock_query = Mock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value.first.side_effect = [None, Mock()]
    
    is_valid, error_msg = LessonService.check_time_conflict(
        mock_session, teacher_id=1, student_id=2,
        lesson_date=date(2024, 3, 15), lesson_time=time(15, 0)
    )
    
    assert is_valid is False
    assert "student already has a lesson" in error_msg


def test_conflict_detection_no_conflict(mock_session):
    """Test no conflict when time slot is available."""
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    is_valid, error_msg = LessonService.check_time_conflict(
        mock_session, teacher_id=1, student_id=2,
        lesson_date=date(2024, 3, 15), lesson_time=time(15, 0)
    )
    
    assert is_valid is True
    assert error_msg == ""


def test_conflict_detection_exclude_current_lesson(mock_session):
    """Test exclude_lesson_id parameter in conflict detection."""
    mock_session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    
    is_valid, error_msg = LessonService.check_time_conflict(
        mock_session, teacher_id=1, student_id=2,
        lesson_date=date(2024, 3, 15), lesson_time=time(15, 0),
        exclude_lesson_id=5
    )
    
    assert is_valid is True
    assert error_msg == ""


def test_create_lesson_past_date_validation(mock_session):
    """Test validation prevents creating lesson in the past."""
    yesterday = date.today() - timedelta(days=1)
    
    success, message, lesson = LessonService.create_lesson(
        mock_session, teacher_id=1, student_id=2,
        lesson_date=yesterday, lesson_time=time(15, 0)
    )
    
    assert success is False
    assert "past date" in message
    assert lesson is None


def test_create_lesson_success(mock_session):
    """Test successful lesson creation."""
    tomorrow = date.today() + timedelta(days=1)
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    mock_lesson = Mock()
    mock_lesson.id = 1
    
    with patch('services.Lesson', return_value=mock_lesson):
        success, message, lesson = LessonService.create_lesson(
            mock_session, teacher_id=1, student_id=2,
            lesson_date=tomorrow, lesson_time=time(15, 0)
        )
    
    assert success is True
    assert "created successfully" in message
    assert lesson is not None
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


def test_reschedule_lesson_success(mock_session):
    """Test successful lesson rescheduling."""
    mock_lesson = Mock()
    mock_lesson.id = 1
    mock_lesson.teacher_id = 1
    mock_lesson.student_id = 2
    mock_lesson.date = date.today() + timedelta(days=1)
    mock_lesson.time = time(15, 0)
    
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_lesson
    mock_session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    
    success, message = LessonService.reschedule_lesson(
        mock_session, lesson_id=1, new_time=time(16, 0)
    )
    
    assert success is True
    assert "rescheduled successfully" in message
    assert mock_lesson.time == time(16, 0)
    mock_session.commit.assert_called_once()


def test_reschedule_lesson_past_date(mock_session):
    """Test validation prevents rescheduling past lessons."""
    mock_lesson = Mock()
    mock_lesson.date = date.today() - timedelta(days=1)
    
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_lesson
    
    success, message = LessonService.reschedule_lesson(
        mock_session, lesson_id=1, new_time=time(16, 0)
    )
    
    assert success is False
    assert "past" in message


def test_cancel_lesson_success(mock_session):
    """Test successful lesson cancellation."""
    mock_lesson = Mock()
    mock_lesson.id = 1
    
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_lesson
    
    success, message, lesson_copy = LessonService.cancel_lesson(
        mock_session, lesson_id=1
    )
    
    assert success is True
    assert "cancelled" in message
    assert lesson_copy is not None
    mock_session.delete.assert_called_once_with(mock_lesson)
    mock_session.commit.assert_called_once()


def test_cancel_lesson_not_found(mock_session):
    """Test error when canceling non-existent lesson."""
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    
    success, message, lesson = LessonService.cancel_lesson(
        mock_session, lesson_id=999
    )
    
    assert success is False
    assert "not found" in message
    assert lesson is None


def test_get_future_lessons(mock_session):
    """Test retrieving future lessons for student."""
    mock_lessons = [Mock(), Mock()]
    mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_lessons
    
    lessons = LessonService.get_future_lessons(mock_session, student_id=1)
    
    assert len(lessons) == 2
    assert lessons == mock_lessons


def test_notification_service_student_notification(mock_bot):
    """Test notification sent to student."""
    mock_student = Mock()
    mock_student.telegram_id = 987654321
    
    mock_teacher = Mock()
    mock_teacher.name = "John Doe"
    
    lesson_date = date(2024, 3, 15)
    lesson_time = time(15, 0)
    
    result = NotificationService.notify_student_lesson_created(
        mock_bot, mock_student, mock_teacher, lesson_date, lesson_time
    )
    
    assert result is True
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args[1]['chat_id'] == 987654321
    assert "John Doe" in call_args[1]['text']
