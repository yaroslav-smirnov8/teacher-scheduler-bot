"""
Homework Service Module
Handles homework CRUD operations and business logic
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select, update, desc, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models import Homework, Lesson, Student, Teacher

logger = logging.getLogger(__name__)


class HomeworkService:
    """Service for managing homework operations"""
    
    @staticmethod
    async def create_homework(
        session: AsyncSession,
        student_id: int,
        teacher_id: int,
        text: str,
        lesson_id: Optional[int] = None,
        json_content: Optional[str] = None,
    ) -> Homework:
        """Create and store homework in database
        
        Args:
            session: Database session
            student_id: ID of student receiving homework
            teacher_id: ID of teacher sending homework
            text: Homework content (plain text with optional URLs)
            lesson_id: Optional ID of associated lesson
            json_content: Optional JSON string for interactive AI homework exercises
            
        Returns:
            Created Homework object
            
        Raises:
            ValueError: If student or teacher not found
        """
        # Verify student exists and belongs to teacher
        student = await session.get(Student, student_id)
        if not student or student.teacher_id != teacher_id:
            raise ValueError(f"Student {student_id} not found or doesn't belong to teacher {teacher_id}")
        
        # Verify teacher exists
        teacher = await session.get(Teacher, teacher_id)
        if not teacher:
            raise ValueError(f"Teacher {teacher_id} not found")
        
        # If lesson_id provided, verify it's valid and belongs to this teacher/student
        if lesson_id:
            lesson = await session.get(Lesson, lesson_id)
            if not lesson or lesson.teacher_id != teacher_id or lesson.student_id != student_id:
                raise ValueError(f"Lesson {lesson_id} invalid or doesn't match teacher/student")
            
            # Check if homework already exists for this lesson (unique constraint)
            existing = await session.execute(
                select(Homework).where(Homework.lesson_id == lesson_id)
            )
            if existing.scalars().first():
                raise ValueError(f"Homework already exists for lesson {lesson_id}")
        
        # Create homework record
        homework = Homework(
            lesson_id=lesson_id,
            student_id=student_id,
            teacher_id=teacher_id,
            text=text,
            json_content=json_content,
            sent_at=datetime.now(timezone.utc),
            status='sent'
        )
        
        session.add(homework)
        await session.flush()  # Ensure ID is generated
        
        logger.info(f"Homework {homework.id} created for student {student_id}")
        
        return homework
    
    @staticmethod
    async def update_homework(
        session: AsyncSession,
        homework_id: int,
        teacher_id: int,
        text: str
    ) -> Homework:
        """Edit homework text (only if not completed)
        
        Args:
            session: Database session
            homework_id: ID of homework to update
            teacher_id: ID of teacher making the edit
            text: New homework text
            
        Returns:
            Updated Homework object
            
        Raises:
            ValueError: If homework not found, doesn't belong to teacher, or is completed
        """
        homework = await session.get(Homework, homework_id)
        if not homework:
            raise ValueError(f"Homework {homework_id} not found")
        
        if homework.teacher_id != teacher_id:
            raise ValueError(f"Homework {homework_id} doesn't belong to teacher {teacher_id}")
        
        if homework.status == 'completed':
            raise ValueError("Cannot edit homework that's already completed")
        
        homework.text = text
        homework.edited_at = datetime.now(timezone.utc)
        homework.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Homework {homework_id} updated by teacher {teacher_id}")
        
        return homework
    
    @staticmethod
    async def delete_homework(
        session: AsyncSession,
        homework_id: int,
        teacher_id: int
    ) -> bool:
        """Delete homework (access controlled)
        
        Args:
            session: Database session
            homework_id: ID of homework to delete
            teacher_id: ID of teacher requesting deletion
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If homework not found or doesn't belong to teacher
        """
        homework = await session.get(Homework, homework_id)
        if not homework:
            raise ValueError(f"Homework {homework_id} not found")
        
        if homework.teacher_id != teacher_id:
            raise ValueError(f"Homework {homework_id} doesn't belong to teacher {teacher_id}")
        
        await session.delete(homework)
        logger.info(f"Homework {homework_id} deleted by teacher {teacher_id}")
        
        return True
    
    @staticmethod
    async def mark_homework_received(
        session: AsyncSession,
        homework_id: int,
        student_id: int
    ) -> Homework:
        """Mark homework as received by student
        
        Args:
            session: Database session
            homework_id: ID of homework
            student_id: ID of student marking as received
            
        Returns:
            Updated Homework object
            
        Raises:
            ValueError: If homework not found or doesn't belong to student
        """
        homework = await session.get(Homework, homework_id)
        if not homework:
            raise ValueError(f"Homework {homework_id} not found")
        
        if homework.student_id != student_id:
            raise ValueError(f"Homework {homework_id} doesn't belong to student {student_id}")
        
        homework.status = 'received'
        homework.received_at = datetime.now(timezone.utc)
        homework.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Homework {homework_id} marked as received by student {student_id}")
        
        return homework
    
    @staticmethod
    async def mark_homework_completed(
        session: AsyncSession,
        homework_id: int,
        student_id: int
    ) -> Homework:
        """Mark homework as completed by student
        
        Args:
            session: Database session
            homework_id: ID of homework
            student_id: ID of student marking as completed
            
        Returns:
            Updated Homework object
            
        Raises:
            ValueError: If homework not found or doesn't belong to student
        """
        homework = await session.get(Homework, homework_id)
        if not homework:
            raise ValueError(f"Homework {homework_id} not found")
        
        if homework.student_id != student_id:
            raise ValueError(f"Homework {homework_id} doesn't belong to student {student_id}")
        
        homework.status = 'completed'
        homework.completed_at = datetime.now(timezone.utc)
        homework.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Homework {homework_id} marked as completed by student {student_id}")
        
        return homework
    
    @staticmethod
    async def get_student_homeworks(
        session: AsyncSession,
        student_id: int,
        limit: int = 50
    ) -> List[Homework]:
        """Get student's homework history (most recent first)
        
        Args:
            session: Database session
            student_id: ID of student
            limit: Max number of records to return
            
        Returns:
            List of Homework objects ordered by sent_at DESC
        """
        result = await session.execute(
            select(Homework)
            .where(Homework.student_id == student_id)
            .order_by(desc(Homework.sent_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_teacher_homeworks(
        session: AsyncSession,
        teacher_id: int,
        limit: int = 50
    ) -> List[Homework]:
        """Get teacher's homework history (most recent first)
        
        Args:
            session: Database session
            teacher_id: ID of teacher
            limit: Max number of records to return
            
        Returns:
            List of Homework objects ordered by sent_at DESC
        """
        result = await session.execute(
            select(Homework)
            .where(Homework.teacher_id == teacher_id)
            .order_by(desc(Homework.sent_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def set_teacher_mark(
        session: AsyncSession,
        homework_id: int,
        teacher_id: int,
        mark: Optional[str],
        optional_done: Optional[bool] = None,
    ) -> Homework:
        """Set teacher evaluation mark on a homework.

        Args:
            session: Database session
            homework_id: ID of homework
            teacher_id: ID of teacher (for access control)
            mark: One of 'not_completed', 'partially_completed', 'main_completed', 'fully_completed', or None to reset
            optional_done: If set, update the optional_done flag

        Returns:
            Updated Homework object

        Raises:
            ValueError: If homework not found or doesn't belong to teacher
        """
        homework = await session.get(Homework, homework_id)
        if not homework:
            raise ValueError(f"Homework {homework_id} not found")
        if homework.teacher_id != teacher_id:
            raise ValueError(f"Homework {homework_id} doesn't belong to teacher {teacher_id}")

        allowed_marks = [None, 'not_completed', 'partially_completed', 'main_completed', 'fully_completed']
        if mark not in allowed_marks:
            raise ValueError(f"Invalid teacher mark: {mark}")

        homework.teacher_mark = mark
        if mark == 'fully_completed':
            homework.optional_done = True
        if optional_done is not None:
            homework.optional_done = optional_done
        homework.updated_at = datetime.now(timezone.utc)

        logger.info(f"Homework {homework_id}: teacher {teacher_id} set mark={mark}, optional_done={homework.optional_done}")
        return homework

    @staticmethod
    async def get_homework_stats(
        session: AsyncSession,
        teacher_id: int,
        student_id: Optional[int] = None,
    ) -> dict:
        """Get homework statistics for a teacher (optionally filtered by student).

        Returns dict with:
            total, completed, main_completed, optional_completed,
            partially_completed, not_completed,
            sent_count, received_count, completion_pct
        """
        conditions = [Homework.teacher_id == teacher_id]
        if student_id is not None:
            conditions.append(Homework.student_id == student_id)

        result = await session.execute(
            select(Homework).where(*conditions)
        )
        all_homeworks = result.scalars().all()
        total = len(all_homeworks)

        completed = 0
        main_completed = 0
        optional_completed = 0
        partially = 0
        not_comp = 0
        sent_count = 0
        received_count = 0

        for hw in all_homeworks:
            tm = hw.teacher_mark
            if tm == 'fully_completed':
                completed += 1
                main_completed += 1
                if hw.optional_done:
                    optional_completed += 1
            elif tm == 'main_completed':
                completed += 1
                main_completed += 1
                if hw.optional_done:
                    optional_completed += 1
            elif tm == 'partially_completed':
                partially += 1
            elif tm == 'not_completed':
                not_comp += 1
            elif tm is None and hw.status == 'completed':
                completed += 1
            elif tm is None and hw.status == 'received':
                received_count += 1
            else:
                sent_count += 1

        return {
            'total': total,
            'completed': completed,
            'main_completed': main_completed,
            'optional_completed': optional_completed,
            'partially_completed': partially,
            'not_completed': not_comp,
            'sent_count': sent_count,
            'received_count': received_count,
            'completion_pct': round(completed / total * 100, 1) if total > 0 else 0.0,
        }

    @staticmethod
    async def get_lesson_homework(
        session: AsyncSession,
        lesson_id: int
    ) -> Optional[Homework]:
        """Get homework linked to a specific lesson (at most 1)
        
        Args:
            session: Database session
            lesson_id: ID of lesson
            
        Returns:
            Homework object or None if not found
        """
        result = await session.execute(
            select(Homework).where(Homework.lesson_id == lesson_id)
        )
        return result.scalar()
    
    @staticmethod
    async def cleanup_old_homework(
        session: AsyncSession,
        days: int = 30
    ) -> int:
        """Delete homework older than specified days using bulk delete.
        
        Removes:
        - Completed homework older than X days
        - Sent (unclaimed) homework older than X days
        
        Args:
            session: Database session
            days: Age threshold in days
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Delete old completed homework (bulk)
        result_completed = await session.execute(
            delete(Homework).where(
                and_(
                    Homework.status == 'completed',
                    Homework.completed_at < cutoff_date
                )
            )
        )
        
        # Delete old unclaimed homework (bulk)
        result_unclaimed = await session.execute(
            delete(Homework).where(
                and_(
                    Homework.status == 'sent',
                    Homework.sent_at < cutoff_date
                )
            )
        )
        
        deleted_count = (result_completed.rowcount or 0) + (result_unclaimed.rowcount or 0)
        logger.info(f"Cleanup: Deleted {deleted_count} old homework records (cutoff: {cutoff_date})")
        
        return deleted_count
    
    @staticmethod
    def format_homework_text(text: str) -> str:
        """Format homework text with URL linkification
        
        Detects plain URLs (https://... or http://...) and returns them
        in a format suitable for Telegram (auto-linkified).
        
        Args:
            text: Raw homework text
            
        Returns:
            Formatted text (URLs are auto-detected by Telegram)
        """
        import re
        
        # Pattern to match http/https URLs
        url_pattern = r'(https?://[^\s]+)'
        
        # Just return as-is - Telegram auto-linkifies URLs
        # This placeholder is for future emoji/link processing
        return text
