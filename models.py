from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from connection import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(10), default='student')  # 'admin' or 'student'

    # Relationship to profile with cascade
    profile = relationship(
        'StudentProfile',
        uselist=False,
        back_populates='user',
        cascade='all, delete-orphan'
    )

    results = relationship('Result', backref='student')


class StudentProfile(Base):
    __tablename__ = 'student_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    full_name = Column(String(100))
    course = Column(String(100))
    level = Column(String(50))
    kasneb_no = Column(String(50))
    profile_completed = Column(Boolean, default=False)

    user = relationship('User', back_populates='profile')

    
class Quiz(Base):
    __tablename__ = 'quizzes'

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    course = Column(String(100), nullable=False)
    subject = Column(String(100), nullable=False)  # Unit
    status = Column(String(50), default='Pending')  # Pending or Done
    duration = Column(Integer, default=30)  # in minutes
    upload_time = Column(DateTime, default=datetime.utcnow)

    questions = relationship('Question', cascade='all, delete-orphan', backref='quiz')
    results = relationship('Result', backref='quiz')

class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)
    text = Column(Text, nullable=False)
    option_a = Column(String(200))
    option_b = Column(String(200))
    option_c = Column(String(200))
    option_d = Column(String(200))
    correct_answer = Column(String(1)) 
    marks = Column(Integer, default=2)

class Result(Base):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'))
    quiz_id = Column(Integer, ForeignKey('quizzes.id'))
    score = Column(Integer)
    taken_on = Column(DateTime, default=datetime.utcnow)