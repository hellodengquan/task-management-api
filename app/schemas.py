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

class RecurrencePlanCreate(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = Field(..., ge=1, le=365)
    week_days: Optional[List[int]] = None
    month_days: Optional[List[int]] = None
    end_date: Optional[datetime] = None
    is_active: bool = True

    @model_validator(mode='after')
    def validate_fields_for_frequency(self) -> 'RecurrencePlanCreate':
        if self.frequency == RecurrenceFrequency.WEEKLY:
            if self.week_days is None or len(self.week_days) == 0:
                raise ValueError("weekly frequency requires week_days to be a non-empty list")
            for day in self.week_days:
                if not (0 <= day <= 6):
                    raise ValueError(f"week_days values must be between 0-6, got {day}")
            if self.month_days is not None and len(self.month_days) > 0:
                raise ValueError("month_days is not allowed for weekly frequency")
        elif self.frequency == RecurrenceFrequency.MONTHLY:
            if self.month_days is None or len(self.month_days) == 0:
                raise ValueError("monthly frequency requires month_days to be a non-empty list")
            for day in self.month_days:
                if not (1 <= day <= 31):
                    raise ValueError(f"month_days values must be between 1-31, got {day}")
            if self.week_days is not None and len(self.week_days) > 0:
                raise ValueError("week_days is not allowed for monthly frequency")
        else:
            if self.week_days is not None and len(self.week_days) > 0:
                raise ValueError(f"week_days is not allowed for {self.frequency} frequency")
            if self.month_days is not None and len(self.month_days) > 0:
                raise ValueError(f"month_days is not allowed for {self.frequency} frequency")
        return self


class RecurrencePlanUpdate(BaseModel):
    frequency: Optional[RecurrenceFrequency] = None
    interval: Optional[int] = Field(default=None, ge=1, le=365)
    week_days: Optional[List[int]] = None
    month_days: Optional[List[int]] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def validate_fields_for_frequency(self) -> 'RecurrencePlanUpdate':
        if self.frequency == RecurrenceFrequency.WEEKLY:
            if self.week_days is not None:
                if len(self.week_days) == 0:
                    raise ValueError("weekly frequency requires week_days to be a non-empty list")
                for day in self.week_days:
                    if not (0 <= day <= 6):
                        raise ValueError(f"week_days values must be between 0-6, got {day}")
            if self.month_days is not None and len(self.month_days) > 0:
                raise ValueError("month_days is not allowed for weekly frequency")
        elif self.frequency == RecurrenceFrequency.MONTHLY:
            if self.month_days is not None:
                if len(self.month_days) == 0:
                    raise ValueError("monthly frequency requires month_days to be a non-empty list")
                for day in self.month_days:
                    if not (1 <= day <= 31):
                        raise ValueError(f"month_days values must be between 1-31, got {day}")
            if self.week_days is not None and len(self.week_days) > 0:
                raise ValueError("week_days is not allowed for monthly frequency")
        elif self.frequency is not None:
            if self.week_days is not None and len(self.week_days) > 0:
                raise ValueError(f"week_days is not allowed for {self.frequency} frequency")
            if self.month_days is not None and len(self.month_days) > 0:
                raise ValueError(f"month_days is not allowed for {self.frequency} frequency")
        
        if self.frequency is None:
            if self.week_days is not None and len(self.week_days) > 0:
                for day in self.week_days:
                    if not (0 <= day <= 6):
                        raise ValueError(f"week_days values must be between 0-6, got {day}")
            if self.month_days is not None and len(self.month_days) > 0:
                for day in self.month_days:
                    if not (1 <= day <= 31):
                        raise ValueError(f"month_days values must be between 1-31, got {day}")
        
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
            data = data.copy()
            if data.get('week_days') and isinstance(data['week_days'], str):
                data['week_days'] = [int(d) for d in data['week_days'].split(',') if d]
            if data.get('month_days') and isinstance(data['month_days'], str):
                data['month_days'] = [int(d) for d in data['month_days'].split(',') if d]
            return data
        elif hasattr(data, '__dict__'):
            obj_dict = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
            if obj_dict.get('week_days') and isinstance(obj_dict['week_days'], str):
                obj_dict['week_days'] = [int(d) for d in obj_dict['week_days'].split(',') if d]
            if obj_dict.get('month_days') and isinstance(obj_dict['month_days'], str):
                obj_dict['month_days'] = [int(d) for d in obj_dict['month_days'].split(',') if d]
            return obj_dict
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
