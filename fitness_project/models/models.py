from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Member(Base):
    __tablename__ = 'Member'
    
    member_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    
   
    fitness_goals = relationship("FitnessGoal", back_populates="member", cascade="all, delete-orphan")
    health_metrics = relationship("HealthMetric", back_populates="member", cascade="all, delete-orphan")
    pt_sessions = relationship("PTSession", back_populates="member", cascade="all, delete-orphan")
    class_enrollments = relationship("ClassEnrollment", back_populates="member", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Member(id={self.member_id}, name='{self.name}', email='{self.email}')>"


class Trainer(Base):
    __tablename__ = 'Trainer'
    
    trainer_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    specialization = Column(String(100), nullable=True)
    
   
    classes = relationship("Class", back_populates="trainer")
    pt_sessions = relationship("PTSession", back_populates="trainer")
    
    def __repr__(self):
        return f"<Trainer(id={self.trainer_id}, name='{self.name}', specialization='{self.specialization}')>"


class Admin(Base):
    __tablename__ = 'Admin'
    
    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # In production, use proper hashing
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    
    def __repr__(self):
        return f"<Admin(id={self.admin_id}, username='{self.username}', name='{self.name}')>"


class FitnessGoal(Base):
    __tablename__ = 'FitnessGoal'
    
    goal_id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('Member.member_id', ondelete='CASCADE'), nullable=False)
    goal_type = Column(String(50), nullable=False)
    target_value = Column(Numeric(6, 2), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    

    member = relationship("Member", back_populates="fitness_goals")
    
    def __repr__(self):
        return f"<FitnessGoal(id={self.goal_id}, member_id={self.member_id}, type='{self.goal_type}')>"


class HealthMetric(Base):
    __tablename__ = 'HealthMetric'
    
    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('Member.member_id', ondelete='CASCADE'), nullable=False)
    metric_type = Column(String(50), nullable=False)
    metric_value = Column(Numeric(6, 2), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    
   
    member = relationship("Member", back_populates="health_metrics")
    
    def __repr__(self):
        return f"<HealthMetric(id={self.metric_id}, member_id={self.member_id}, type='{self.metric_type}')>"


class Room(Base):
    __tablename__ = 'Room'
    
    room_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    
 
    classes = relationship("Class", back_populates="room")
    
    
    __table_args__ = (
        CheckConstraint('capacity > 0', name='check_capacity_positive'),
    )
    
    def __repr__(self):
        return f"<Room(id={self.room_id}, name='{self.name}', capacity={self.capacity})>"


class Class(Base):
    __tablename__ = 'Class'
    
    class_id = Column(Integer, primary_key=True, autoincrement=True)
    trainer_id = Column(Integer, ForeignKey('Trainer.trainer_id', ondelete='RESTRICT'), nullable=False)
    room_id = Column(Integer, ForeignKey('Room.room_id', ondelete='RESTRICT'), nullable=False)
    class_name = Column(String(100), nullable=False)
    class_time = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    
   
    trainer = relationship("Trainer", back_populates="classes")
    room = relationship("Room", back_populates="classes")
    enrollments = relationship("ClassEnrollment", back_populates="class_obj", cascade="all, delete-orphan")
    
    
    __table_args__ = (
        CheckConstraint('capacity > 0', name='check_class_capacity_positive'),
        UniqueConstraint('room_id', 'class_time', name='uq_room_time'),
    )
    
    def __repr__(self):
        return f"<Class(id={self.class_id}, name='{self.class_name}', time={self.class_time})>"


class PTSession(Base):
    __tablename__ = 'PTSession'
    
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('Member.member_id', ondelete='CASCADE'), nullable=False)
    trainer_id = Column(Integer, ForeignKey('Trainer.trainer_id', ondelete='RESTRICT'), nullable=False)
    session_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default='scheduled')
    
 
    member = relationship("Member", back_populates="pt_sessions")
    trainer = relationship("Trainer", back_populates="pt_sessions")
    
   
    __table_args__ = (
        UniqueConstraint('trainer_id', 'session_time', name='uq_trainer_time'),
        Index('idx_ptsession_trainer_time', 'trainer_id', 'session_time'),
    )
    
    def __repr__(self):
        return f"<PTSession(id={self.session_id}, member_id={self.member_id}, trainer_id={self.trainer_id}, time={self.session_time})>"


class ClassEnrollment(Base):
    __tablename__ = 'ClassEnrollment'
    
    enrollment_id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('Member.member_id', ondelete='CASCADE'), nullable=False)
    class_id = Column(Integer, ForeignKey('Class.class_id', ondelete='CASCADE'), nullable=False)
    enrollment_date = Column(DateTime, nullable=False, default=datetime.now)
    
    member = relationship("Member", back_populates="class_enrollments")
    class_obj = relationship("Class", back_populates="enrollments")
    
    __table_args__ = (
        UniqueConstraint('member_id', 'class_id', name='uq_member_class'),
    )
    
    def __repr__(self):
        return f"<ClassEnrollment(id={self.enrollment_id}, member_id={self.member_id}, class_id={self.class_id})>"
