"""Access control service for lesson deletion operations"""
from typing import Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Lesson, RecurringPattern


class AccessControlService:
    """Service for controlling access to lesson deletion operations"""
    
    @staticmethod
    async def verify_teacher_owns_lesson(
        session: AsyncSession,
        teacher_id: int,
        lesson_id: int
    ) -> Tuple[bool, str]:
        """Verify that a teacher owns a specific lesson
        
        Args:
            session: Database session
            teacher_id: ID of the teacher to verify
            lesson_id: ID of the lesson to check
            
        Returns:
            Tuple of (success, error_message):
            - (True, "") if teacher owns the lesson
            - (False, error_message) if teacher doesn't own or lesson not found
            
        Security Property:
            ∀ lesson_id, teacher_id: verify_teacher_owns_lesson(teacher_id, lesson_id) = True 
            ⟹ lesson.teacher_id = teacher_id
        """
        # Query the lesson to get its teacher_id
        result = await session.execute(
            select(Lesson).filter_by(id=lesson_id)
        )
        lesson = result.scalar_one_or_none()
        
        if lesson is None:
            return False, "Lesson not found"
        
        if lesson.teacher_id != teacher_id:
            return False, "Access denied: only the lesson's teacher can perform this operation"
        
        return True, ""
    
    @staticmethod
    async def verify_teacher_owns_pattern(
        session: AsyncSession,
        teacher_id: int,
        pattern_id: int
    ) -> Tuple[bool, str]:
        """Verify that a teacher owns a specific recurring pattern
        
        Args:
            session: Database session
            teacher_id: ID of the teacher to verify
            pattern_id: ID of the recurring pattern to check
            
        Returns:
            Tuple of (success, error_message):
            - (True, "") if teacher owns the pattern
            - (False, error_message) if teacher doesn't own or pattern not found
            
        Security Property:
            ∀ pattern_id, teacher_id: verify_teacher_owns_pattern(teacher_id, pattern_id) = True 
            ⟹ pattern.teacher_id = teacher_id
        """
        # Query the pattern to get its teacher_id
        result = await session.execute(
            select(RecurringPattern).filter_by(id=pattern_id)
        )
        pattern = result.scalar_one_or_none()
        
        if pattern is None:
            return False, "Recurring pattern not found"
        
        if pattern.teacher_id != teacher_id:
            return False, "Access denied: only the pattern's teacher can perform this operation"
        
        return True, ""
