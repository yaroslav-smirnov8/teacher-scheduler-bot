"""Reschedule service - Managing lesson reschedule requests"""
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Student, Lesson, RescheduleRequest
from services.lesson_service import LessonService
import logging

logger = logging.getLogger(__name__)


class RescheduleService:
    """Service for managing lesson reschedule requests.
    
    Handles student requests to reschedule lessons and teacher approval/decline.
    Enforces weekly reschedule limits (max 2 per rolling 7-day window).
    """
    
    @staticmethod
    async def check_reschedule_limit(session: AsyncSession, student_id: int) -> Tuple[bool, str]:
        """Check if student has exceeded weekly reschedule limit."""
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        result = await session.execute(
            select(RescheduleRequest).filter(
                RescheduleRequest.student_id == student_id,
                RescheduleRequest.created_at >= seven_days_ago
            )
        )
        recent_requests = result.scalars().all()
        
        if len(recent_requests) >= 2:
            return False, "You have reached the weekly limit of 2 reschedule requests. Please try again later."
        
        return True, ""
    
    @staticmethod
    async def create_reschedule_request(
        session: AsyncSession,
        lesson_id: int,
        student_id: int,
        teacher_id: int,
        original_date: date,
        original_time: time,
        requested_date: date,
        requested_time: time,
        reason: str
    ) -> Tuple[bool, str, Optional[RescheduleRequest]]:
        """Create a reschedule request (thread-safe via SELECT ... FOR UPDATE on student row to serialize requests per student)."""
        # Lock the student row to serialize concurrent reschedule requests for the same student
        student_check = await session.execute(
            select(Student).filter_by(id=student_id).with_for_update()
        )
        if not student_check.scalar_one_or_none():
            return False, "Student not found", None

        can_request, error_msg = await RescheduleService.check_reschedule_limit(session, student_id)
        if not can_request:
            return False, error_msg, None

        if requested_date < datetime.now(timezone.utc).date():
            return False, "Cannot reschedule to a past date", None

        is_valid, conflict_msg = await LessonService.check_time_conflict(
            session, teacher_id, student_id, requested_date, requested_time, exclude_lesson_id=lesson_id
        )
        if not is_valid:
            return False, conflict_msg, None

        try:
            request = RescheduleRequest(
                lesson_id=lesson_id,
                student_id=student_id,
                teacher_id=teacher_id,
                original_date=original_date,
                original_time=original_time,
                requested_date=requested_date,
                requested_time=requested_time,
                reason=reason,
                status='pending',
                created_at=datetime.now(timezone.utc)
            )

            session.add(request)
            await session.commit()
            await session.refresh(request)

            return True, "Reschedule request created successfully", request

        except Exception as e:
            await session.rollback()
            logger.error("Error creating reschedule request: %s", e)
            return False, "Error creating reschedule request. Please try again.", None
    
    @staticmethod
    async def approve_reschedule(
        session: AsyncSession,
        request_id: int
    ) -> Tuple[bool, str, Optional[Lesson]]:
        """Approve a reschedule request."""
        result = await session.execute(
            select(RescheduleRequest).filter_by(id=request_id).with_for_update()
        )
        request = result.scalar_one_or_none()
        
        if not request:
            return False, "Reschedule request not found", None
        
        if request.status != 'pending':
            return False, f"Request has already been {request.status}", None
        
        try:
            result = await session.execute(select(Lesson).filter_by(id=request.lesson_id))
            lesson = result.scalar_one_or_none()
            
            if not lesson:
                return False, "Lesson not found", None
            
            is_valid, conflict_msg = await LessonService.check_time_conflict(
                session, request.teacher_id, request.student_id,
                request.requested_date, request.requested_time,
                exclude_lesson_id=request.lesson_id
            )
            if not is_valid:
                return False, conflict_msg, None
            
            lesson.date = request.requested_date
            lesson.time = request.requested_time
            
            request.status = 'approved'
            request.reviewed_at = datetime.now(timezone.utc)
            
            await session.commit()
            await session.refresh(lesson)
            
            return True, "Reschedule approved", lesson
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error approving reschedule: {e}")
            return False, "Error approving reschedule. Please try again.", None
    
    @staticmethod
    async def decline_reschedule(
        session: AsyncSession,
        request_id: int
    ) -> Tuple[bool, str]:
        """Decline a reschedule request."""
        result = await session.execute(select(RescheduleRequest).filter_by(id=request_id))
        request = result.scalar_one_or_none()
        
        if not request:
            return False, "Reschedule request not found"
        
        if request.status != 'pending':
            return False, f"Request has already been {request.status}"
        
        try:
            request.status = 'declined'
            request.reviewed_at = datetime.now(timezone.utc)
            
            await session.commit()
            
            return True, "Reschedule request declined"
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error declining reschedule: {e}")
            return False, "Error declining reschedule. Please try again."
    
    @staticmethod
    async def get_pending_requests(
        session: AsyncSession,
        teacher_id: int
    ) -> List[RescheduleRequest]:
        """Get all pending reschedule requests for a teacher."""
        result = await session.execute(
            select(RescheduleRequest).filter(
                RescheduleRequest.teacher_id == teacher_id,
                RescheduleRequest.status == 'pending'
            ).order_by(RescheduleRequest.created_at)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_student_future_lessons(
        session: AsyncSession,
        student_id: int
    ) -> List[Lesson]:
        """Get future lessons for a student (for reschedule selection)."""
        today = datetime.now(timezone.utc).date()
        result = await session.execute(
            select(Lesson).filter(
                Lesson.student_id == student_id,
                Lesson.date >= today
            ).order_by(Lesson.date, Lesson.time)
        )
        return result.scalars().all()
