"""Feedback service - Managing student feedback"""
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Student, StudentFeedback
import logging

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for managing student feedback."""
    
    @staticmethod
    async def create_feedback(
        session: AsyncSession,
        student_id: int,
        student_name: str,
        message_text: str
    ) -> Tuple[bool, str, Optional[StudentFeedback]]:
        """Create a new feedback entry."""
        try:
            feedback = StudentFeedback(
                student_id=student_id,
                student_name=student_name,
                message_text=message_text,
                created_at=datetime.now(timezone.utc),
                is_read=False
            )
            
            session.add(feedback)
            await session.commit()
            await session.refresh(feedback)
            
            return True, "Feedback created successfully", feedback
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating feedback: {e}")
            return False, "Error creating feedback. Please try again.", None
    
    @staticmethod
    async def get_feedback_by_student(
        session: AsyncSession,
        student_id: int
    ) -> List[StudentFeedback]:
        """Get all feedback for a specific student."""
        result = await session.execute(
            select(StudentFeedback).filter_by(student_id=student_id)
            .order_by(StudentFeedback.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_all_feedback(session: AsyncSession, teacher_id: int) -> dict:
        """Get feedback grouped by student, filtered by teacher ownership."""
        result = await session.execute(
            select(StudentFeedback).join(
                Student, StudentFeedback.student_id == Student.id
            ).filter(
                Student.teacher_id == teacher_id
            ).order_by(StudentFeedback.created_at.desc())
        )
        all_feedback = result.scalars().all()
        
        grouped = {}
        for feedback in all_feedback:
            if feedback.student_id not in grouped:
                grouped[feedback.student_id] = []
            grouped[feedback.student_id].append(feedback)
        
        return grouped
    
    @staticmethod
    async def get_feedback_by_id(
        session: AsyncSession,
        feedback_id: int
    ) -> Optional[StudentFeedback]:
        """Get a single feedback item by ID."""
        result = await session.execute(
            select(StudentFeedback).filter_by(id=feedback_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def mark_as_read(
        session: AsyncSession,
        feedback_id: int
    ) -> Tuple[bool, str]:
        """Mark feedback as read."""
        result = await session.execute(
            select(StudentFeedback).filter_by(id=feedback_id)
        )
        feedback = result.scalar_one_or_none()
        
        if not feedback:
            return False, "Feedback not found"
        
        try:
            feedback.is_read = True
            await session.commit()
            return True, "Feedback marked as read"
        except Exception as e:
            await session.rollback()
            logger.error("Error marking feedback as read: %s", e)
            return False, "Feedback error"
