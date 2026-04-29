# app/models.py
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Enum
from sqlalchemy.orm import relationship

from .db import Base


class RecurrenceFrequency(PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurrencePlan(Base):
    __tablename__ = "recurrence_plans"

    id = Column(Integer, primary_key=True, index=True)
    frequency = Column(
        Enum(RecurrenceFrequency, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    interval = Column(Integer, default=1, nullable=False)
    week_days = Column(String(255), nullable=True)
    month_days = Column(String(255), nullable=True)
    end_date = Column(DateTime, nullable=True)
    last_generated = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User")
    tasks = relationship("Task", back_populates="recurrence_plan")
    skipped_occurrences = relationship("SkippedOccurrence", back_populates="recurrence_plan")


class SkippedOccurrence(Base):
    __tablename__ = "skipped_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    occurrence_date = Column(DateTime, nullable=False)
    reason = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recurrence_plan_id = Column(Integer, ForeignKey("recurrence_plans.id"), nullable=False)
    recurrence_plan = relationship("RecurrencePlan", back_populates="skipped_occurrences")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    tasks = relationship(
        "Task",
        back_populates="owner",
        cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    due_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recurrence_plan_id = Column(Integer, ForeignKey("recurrence_plans.id"), nullable=True)

    owner = relationship("User", back_populates="tasks")
    recurrence_plan = relationship("RecurrencePlan", back_populates="tasks")
