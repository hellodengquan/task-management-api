# app/schemas.py
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from enum import Enum as PyEnum


class RecurrenceFrequency(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


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
# RECURRENCE PLANS
# =====================

def _validate_recurrence_fields(
    frequency: Optional[RecurrenceFrequency],
    week_days: Optional[List[int]],
    month_days: Optional[List[int]],
    is_update: bool = False
) -> None:
    """
    Validate recurrence fields based on frequency.
    For updates, only validate if frequency is provided.
    """
    if frequency is None:
        return
    
    if week_days is not None:
        for day in week_days:
            if day < 0 or day > 6:
                raise ValueError(f"week_days must be between 0 and 6, got {day}")
    
    if month_days is not None:
        for day in month_days:
            if day < 1 or day > 31:
                raise ValueError(f"month_days must be between 1 and 31, got {day}")
    
    if frequency == RecurrenceFrequency.WEEKLY:
        if month_days is not None:
            raise ValueError("month_days is not allowed for weekly frequency")
    
    elif frequency == RecurrenceFrequency.MONTHLY:
        if week_days is not None:
            raise ValueError("week_days is not allowed for monthly frequency")
    
    elif frequency in [RecurrenceFrequency.DAILY, RecurrenceFrequency.YEARLY]:
        if week_days is not None:
            raise ValueError(f"week_days is not allowed for {frequency.value} frequency")
        if month_days is not None:
            raise ValueError(f"month_days is not allowed for {frequency.value} frequency")


class RecurrencePlanCreate(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = Field(..., ge=1, le=365)
    week_days: Optional[List[int]] = Field(default=None, min_length=0, max_length=7)
    month_days: Optional[List[int]] = Field(default=None, min_length=0, max_length=31)
    end_date: Optional[datetime] = None
    is_active: bool = True

    @model_validator(mode='after')
    def validate_recurrence(self) -> 'RecurrencePlanCreate':
        _validate_recurrence_fields(self.frequency, self.week_days, self.month_days)
        return self


class RecurrencePlanUpdate(BaseModel):
    frequency: Optional[RecurrenceFrequency] = None
    interval: Optional[int] = Field(default=None, ge=1, le=365)
    week_days: Optional[List[int]] = Field(default=None, min_length=0, max_length=7)
    month_days: Optional[List[int]] = Field(default=None, min_length=0, max_length=31)
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def validate_recurrence(self) -> 'RecurrencePlanUpdate':
        _validate_recurrence_fields(self.frequency, self.week_days, self.month_days, is_update=True)
        return self


class RecurrencePlanOut(BaseModel):
    id: int
    frequency: RecurrenceFrequency
    interval: int
    week_days: Optional[List[int]] = None
    month_days: Optional[List[int]] = None
    end_date: Optional[datetime] = None
    last_generated: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def convert_comma_strings(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get('week_days') and isinstance(data['week_days'], str):
                data['week_days'] = [int(d) for d in data['week_days'].split(',') if d]
            if data.get('month_days') and isinstance(data['month_days'], str):
                data['month_days'] = [int(d) for d in data['month_days'].split(',') if d]
        else:
            if hasattr(data, 'week_days') and data.week_days and isinstance(data.week_days, str):
                data.week_days = [int(d) for d in data.week_days.split(',') if d]
            if hasattr(data, 'month_days') and data.month_days and isinstance(data.month_days, str):
                data.month_days = [int(d) for d in data.month_days.split(',') if d]
        return data


# =====================
# SKIPPED OCCURRENCES
# =====================

class SkippedOccurrenceCreate(BaseModel):
    occurrence_date: datetime
    reason: Optional[str] = Field(default=None, max_length=500)


class SkippedOccurrenceOut(BaseModel):
    id: int
    recurrence_plan_id: int
    occurrence_date: datetime
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================
# TASKS
# =====================

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    due_date: Optional[datetime] = None
    recurrence_plan_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    completed: Optional[bool] = None
    due_date: Optional[datetime] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    recurrence_plan_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
