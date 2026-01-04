"""Database models"""
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time, BigInteger
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_info = Column(String(100))
    login = Column(String(100), unique=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    students = relationship("Student", back_populates="teacher", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="teacher", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_info = Column(String(100))
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    telegram_id = Column(BigInteger, unique=True)
    teacher = relationship("Teacher", back_populates="students")
    lessons = relationship("Lesson", back_populates="student", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    teacher = relationship("Teacher", back_populates="lessons")
    student = relationship("Student", back_populates="lessons")
