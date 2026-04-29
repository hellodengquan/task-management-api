# app/schemas.py
from datetime import datetime
from typing import Optional, List, Any
import enum

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =====================
# USERS
# =====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================
# AUTH
# =====================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =====================
# TASKS
# =====================

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    assignee_id: Optional[int] = Field(default=None)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    completed: Optional[bool] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[int] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
    status: TaskStatus
    priority: TaskPriority
    owner_id: int
    assignee_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================
# BATCH OPERATIONS
# =====================

class BatchUpdateRequest(BaseModel):
    task_ids: List[int]
    updates: TaskUpdate


class BatchDeleteRequest(BaseModel):
    task_ids: List[int]


class BatchOperationResult(BaseModel):
    success: bool
    task_id: int
    detail: Optional[str] = None


class BatchUpdateResponse(BaseModel):
    total: int
    success_count: int
    failure_count: int
    successes: List[TaskOut]
    failures: List[BatchOperationResult]


class BatchDeleteResponse(BaseModel):
    total: int
    success_count: int
    failure_count: int
    successes: List[BatchOperationResult]
    failures: List[BatchOperationResult]