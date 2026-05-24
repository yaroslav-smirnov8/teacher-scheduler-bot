"""Database models"""
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time, BigInteger, CheckConstraint, UniqueConstraint, Index, DateTime, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship, declarative_base, validates
from datetime import datetime, timezone

Base = declarative_base()


def utcnow():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_info = Column(String(100))
    login = Column(String(100), unique=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    students = relationship("Student", back_populates="teacher", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="teacher", cascade="all, delete-orphan")
    recurring_patterns = relationship("RecurringPattern", back_populates="teacher", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="teacher", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_info = Column(String(100))
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    telegram_id = Column(BigInteger, unique=True)
    payment_reminders_enabled = Column(Boolean, nullable=False, default=False)  # Whether student receives payment reminders
    paid_lessons_balance = Column(Integer, nullable=False, default=0)  # Remaining prepaid lesson count
    teacher = relationship("Teacher", back_populates="students")
    lessons = relationship("Lesson", back_populates="student", cascade="all, delete-orphan")
    recurring_patterns = relationship("RecurringPattern", back_populates="student", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="student", cascade="all, delete-orphan")
    payment_transactions = relationship("PaymentTransaction", back_populates="student", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    recurring_pattern_id = Column(Integer, ForeignKey('recurring_patterns.id'), nullable=True)
    lesson_completed_at = Column(DateTime, nullable=True)  # When lesson ends (for homework prompts)
    homework_prompt_sent_at = Column(DateTime, nullable=True)  # When homework prompt was sent (prevents duplicates)
    is_paid = Column(Boolean, nullable=False, default=False)  # Payment status
    paid_at = Column(DateTime, nullable=True)  # When payment was marked
    paid_by_admin_id = Column(Integer, nullable=True)  # Telegram ID of admin who marked payment
    payment_note = Column(String(500), nullable=True)  # Optional payment note
    payment_reminder_sent_at = Column(DateTime, nullable=True)  # When payment reminder was sent
    paid_from_balance = Column(Boolean, nullable=False, default=False)  # Was this lesson paid from balance
    teacher = relationship("Teacher", back_populates="lessons")
    student = relationship("Student", back_populates="lessons")
    recurring_pattern = relationship("RecurringPattern", foreign_keys=[recurring_pattern_id], back_populates="lessons")
    
    __table_args__ = (
        UniqueConstraint('teacher_id', 'date', 'time', name='uq_lesson_teacher_date_time'),
        Index('idx_lessons_pattern', 'recurring_pattern_id', 'date'),
        Index('idx_lessons_teacher_date', 'teacher_id', 'date'),
        Index('idx_lessons_student_date', 'student_id', 'date'),
        Index('idx_lessons_homework_check', 'date', 'time', 'homework_prompt_sent_at'),
        Index('idx_lessons_is_paid', 'is_paid'),
        Index('idx_lessons_teacher', 'teacher_id'),
        Index('idx_lessons_student', 'student_id'),
    )


class RecurringPattern(Base):
    __tablename__ = 'recurring_patterns'
    
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    time = Column(Time, nullable=False)
    frequency = Column(String(20), nullable=False)
    interval = Column(Integer, nullable=False, default=1)
    weekday = Column(Integer)
    day_of_month = Column(Integer)
    created_from_lesson_id = Column(Integer, ForeignKey('lessons.id'))
    
    # Relationships
    teacher = relationship("Teacher", back_populates="recurring_patterns")
    student = relationship("Student", back_populates="recurring_patterns")
    lessons = relationship("Lesson", foreign_keys="[Lesson.recurring_pattern_id]", back_populates="recurring_pattern")
    exceptions = relationship("RecurringException", back_populates="pattern", cascade="all, delete-orphan")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("frequency IN ('weekly', 'biweekly', 'monthly')", name='check_frequency'),
        Index('idx_recurring_patterns_teacher', 'teacher_id', 'start_date'),
        Index('idx_recurring_patterns_student', 'student_id', 'start_date'),
    )
    
    @validates('frequency')
    def validate_frequency(self, key, value):
        """Validate that frequency is one of the allowed values"""
        allowed_frequencies = ['weekly', 'biweekly', 'monthly']
        if value not in allowed_frequencies:
            raise ValueError(f"Frequency must be one of {allowed_frequencies}, got '{value}'")
        return value


class RecurringException(Base):
    __tablename__ = 'recurring_exceptions'
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(Integer, ForeignKey('recurring_patterns.id'), nullable=False)
    exception_date = Column(Date, nullable=False)
    reason = Column(String(200))
    
    # Relationships
    pattern = relationship("RecurringPattern", back_populates="exceptions")
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('pattern_id', 'exception_date', name='uq_pattern_exception_date'),
        Index('idx_recurring_exceptions_pattern', 'pattern_id', 'exception_date'),
    )


class RescheduleRequest(Base):
    __tablename__ = 'reschedule_requests'
    
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    original_date = Column(Date, nullable=False)
    original_time = Column(Time, nullable=False)
    requested_date = Column(Date, nullable=False)
    requested_time = Column(Time, nullable=False)
    reason = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(DateTime, nullable=False, default=utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    lesson = relationship("Lesson")
    student = relationship("Student")
    teacher = relationship("Teacher")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'declined')", name='check_reschedule_status'),
        Index('idx_reschedule_requests_student', 'student_id', 'created_at'),
        Index('idx_reschedule_requests_teacher', 'teacher_id', 'status'),
        Index('idx_reschedule_requests_lesson', 'lesson_id'),
    )
    
    @validates('status')
    def validate_status(self, key, value):
        """Validate that status is one of the allowed values"""
        allowed_statuses = ['pending', 'approved', 'declined']
        if value not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}, got '{value}'")
        return value


class StudentFeedback(Base):
    __tablename__ = 'student_feedback'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    student_name = Column(String(100), nullable=False)
    message_text = Column(String(1000), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    is_read = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    student = relationship("Student")
    
    # Table constraints
    __table_args__ = (
        Index('idx_feedback_student', 'student_id', 'created_at'),
        Index('idx_feedback_read', 'is_read', 'created_at'),
    )


class Homework(Base):
    __tablename__ = 'homeworks'
    
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=True)  # Can be NULL for independent homework
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    text = Column(String(10000), nullable=False)  # Homework content (text only)
    json_content = Column(String(10000), nullable=True)  # AI homework JSON for interactive exercises
    sent_at = Column(DateTime, nullable=False, default=utcnow)  # When sent to student
    status = Column(String(20), nullable=False, default='sent')  # sent | received | completed
    teacher_mark = Column(String(30), nullable=True)  # not_completed | partially_completed | main_completed | fully_completed
    optional_done = Column(Boolean, nullable=False, default=False)  # Teacher: optional part completed
    
    received_at = Column(DateTime, nullable=True)  # When student marked as received
    completed_at = Column(DateTime, nullable=True)  # When student marked as completed
    edited_at = Column(DateTime, nullable=True)  # Last edit timestamp
    
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    
    # Relationships
    lesson = relationship("Lesson")
    student = relationship("Student", back_populates="homeworks")
    teacher = relationship("Teacher", back_populates="homeworks")
    attempts = relationship("HomeworkAttempt", back_populates="homework", cascade="all, delete-orphan")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("status IN ('sent', 'received', 'completed')", name='check_homework_status'),
        UniqueConstraint('lesson_id', name='uq_homework_lesson_id'),
        Index('idx_homeworks_student_sent', 'student_id', 'sent_at'),
        Index('idx_homeworks_teacher_sent', 'teacher_id', 'sent_at'),
        Index('idx_homeworks_lesson', 'lesson_id'),
        Index('idx_homeworks_cleanup', 'status', 'created_at'),
        Index('idx_homeworks_sent_status', 'status', 'sent_at'),
    )
    
    @validates('status')
    def validate_status(self, key, value):
        """Validate that status is one of the allowed values"""
        allowed_statuses = ['sent', 'received', 'completed']
        if value not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}, got '{value}'")
        return value


class PaymentTransaction(Base):
    __tablename__ = 'payment_transactions'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    type = Column(String(20), nullable=False)  # payment | apply | refund | forfeit
    amount = Column(Integer, nullable=False)  # positive = credit, negative = debit
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=True)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    student = relationship("Student", back_populates="payment_transactions")
    teacher = relationship("Teacher")
    lesson = relationship("Lesson")

    __table_args__ = (
        CheckConstraint("type IN ('payment', 'apply', 'refund', 'forfeit')", name='check_txn_type'),
        Index('idx_payment_txn_student', 'student_id', 'created_at'),
        Index('idx_payment_txn_teacher', 'teacher_id', 'created_at'),
        Index('idx_payment_txn_lesson', 'lesson_id'),
    )

    @validates('type')
    def validate_type(self, key, value):
        allowed = ('payment', 'apply', 'refund', 'forfeit')
        if value not in allowed:
            raise ValueError(f"Transaction type must be one of {allowed}, got '{value}'")
        return value


class HomeworkAttempt(Base):
    __tablename__ = 'homework_attempts'
    
    id = Column(Integer, primary_key=True)
    homework_id = Column(Integer, ForeignKey('homeworks.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    results = Column(String(10000), nullable=False)  # JSON array of [{idx, type, correct, answer}]
    score = Column(Integer, nullable=False)  # Number of correct answers
    total = Column(Integer, nullable=False)  # Total exercises
    started_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    homework = relationship("Homework", back_populates="attempts")
    student = relationship("Student")
    
    __table_args__ = (
        Index('idx_homework_attempts_hw', 'homework_id', 'completed_at'),
        Index('idx_homework_attempts_student', 'student_id', 'completed_at'),
    )
