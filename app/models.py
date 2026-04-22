# app/models.py
from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship, validates

from .db import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


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
    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="tasks")

    _syncing = False

    @validates("status")
    def sync_completed_with_status(self, key, value):
        if not self._syncing:
            self._syncing = True
            try:
                self.completed = value == TaskStatus.COMPLETED
            finally:
                self._syncing = False
        return value

    @validates("completed")
    def sync_status_with_completed(self, key, value):
        if not self._syncing:
            self._syncing = True
            try:
                if value and self.status != TaskStatus.COMPLETED:
                    self.status = TaskStatus.COMPLETED
                elif not value and self.status == TaskStatus.COMPLETED:
                    self.status = TaskStatus.PENDING
            finally:
                self._syncing = False
        return value
