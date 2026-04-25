# app/schemas.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


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
# TAGS
# =====================

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#3b82f6", min_length=7, max_length=7)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not v.startswith("#"):
            raise ValueError("Color must start with #")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must be a valid hex color")
        return v.upper()


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    color: Optional[str] = Field(default=None, min_length=7, max_length=7)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.startswith("#"):
            raise ValueError("Color must start with #")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must be a valid hex color")
        return v.upper()


class TagOut(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagReference(BaseModel):
    id: int
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)


# =====================
# TASKS
# =====================

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    tag_ids: Optional[List[int]] = Field(default=None)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    completed: Optional[bool] = None
    tag_ids: Optional[List[int]] = Field(default=None)


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    updated_at: datetime
    tags: List[TagReference] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
