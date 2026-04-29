# app/crud.py
from datetime import datetime, date as datetime_date
from typing import List, Optional

from sqlalchemy import Date
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import hash_password, verify_password


# =====================
# UTILITY FUNCTIONS
# =====================

def list_to_comma_string(lst: Optional[List[int]]) -> Optional[str]:
    if lst is None:
        return None
    return ','.join(str(d) for d in lst) if lst else None


def comma_string_to_list(s: Optional[str]) -> Optional[List[int]]:
    if s is None:
        return None
    return [int(d) for d in s.split(',') if d] if s else None


# =====================
# USERS
# =====================

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_in: schemas.UserCreate):
    existing = get_user_by_email(db, user_in.email)
    if existing:
        return None  # caller will handle error

    user = models.User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# =====================
# RECURRENCE PLANS
# =====================

def create_recurrence_plan(db: Session, owner_id: int, plan_in: schemas.RecurrencePlanCreate):
    plan = models.RecurrencePlan(
        frequency=plan_in.frequency,
        interval=plan_in.interval,
        week_days=list_to_comma_string(plan_in.week_days),
        month_days=list_to_comma_string(plan_in.month_days),
        end_date=plan_in.end_date,
        is_active=plan_in.is_active,
        owner_id=owner_id,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_recurrence_plans(db: Session, owner_id: int):
    return (
        db.query(models.RecurrencePlan)
        .filter(models.RecurrencePlan.owner_id == owner_id)
        .order_by(models.RecurrencePlan.created_at.desc())
        .all()
    )


def get_recurrence_plan(db: Session, owner_id: int, plan_id: int):
    return (
        db.query(models.RecurrencePlan)
        .filter(models.RecurrencePlan.owner_id == owner_id, models.RecurrencePlan.id == plan_id)
        .first()
    )


def update_recurrence_plan(db: Session, owner_id: int, plan_id: int, updates: schemas.RecurrencePlanUpdate):
    plan = get_recurrence_plan(db, owner_id, plan_id)
    if not plan:
        return None

    if updates.frequency is not None:
        plan.frequency = updates.frequency
    if updates.interval is not None:
        plan.interval = updates.interval
    if updates.week_days is not None:
        plan.week_days = list_to_comma_string(updates.week_days)
    if updates.month_days is not None:
        plan.month_days = list_to_comma_string(updates.month_days)
    if updates.end_date is not None:
        plan.end_date = updates.end_date
    if updates.is_active is not None:
        plan.is_active = updates.is_active

    db.commit()
    db.refresh(plan)
    return plan


def delete_recurrence_plan(db: Session, owner_id: int, plan_id: int) -> bool:
    plan = get_recurrence_plan(db, owner_id, plan_id)
    if not plan:
        return False

    db.delete(plan)
    db.commit()
    return True


# =====================
# SKIPPED OCCURRENCES
# =====================

def create_skipped_occurrence(db: Session, plan_id: int, occurrence_in: schemas.SkippedOccurrenceCreate):
    skipped = models.SkippedOccurrence(
        recurrence_plan_id=plan_id,
        occurrence_date=occurrence_in.occurrence_date,
        reason=occurrence_in.reason,
    )
    db.add(skipped)
    db.commit()
    db.refresh(skipped)
    return skipped


def list_skipped_occurrences(db: Session, plan_id: int):
    return (
        db.query(models.SkippedOccurrence)
        .filter(models.SkippedOccurrence.recurrence_plan_id == plan_id)
        .order_by(models.SkippedOccurrence.occurrence_date.desc())
        .all()
    )


def is_occurrence_skipped(db: Session, plan_id: int, occurrence_date: datetime) -> bool:
    target_date = occurrence_date.date()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    return (
        db.query(models.SkippedOccurrence)
        .filter(
            models.SkippedOccurrence.recurrence_plan_id == plan_id,
            models.SkippedOccurrence.occurrence_date >= start_of_day,
            models.SkippedOccurrence.occurrence_date <= end_of_day
        )
        .first() is not None
    )


# =====================
# TASKS
# =====================

def create_task(db: Session, owner_id: int, task_in: schemas.TaskCreate):
    task = models.Task(
        title=task_in.title,
        description=task_in.description,
        due_date=task_in.due_date,
        recurrence_plan_id=task_in.recurrence_plan_id,
        owner_id=owner_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, owner_id: int):
    return (
        db.query(models.Task)
        .filter(models.Task.owner_id == owner_id)
        .order_by(models.Task.created_at.desc())
        .all()
    )


def get_task(db: Session, owner_id: int, task_id: int):
    return (
        db.query(models.Task)
        .filter(models.Task.owner_id == owner_id, models.Task.id == task_id)
        .first()
    )


def update_task(db: Session, owner_id: int, task_id: int, updates: schemas.TaskUpdate):
    task = get_task(db, owner_id, task_id)
    if not task:
        return None

    if updates.title is not None:
        task.title = updates.title
    if updates.description is not None:
        task.description = updates.description
    if updates.completed is not None:
        task.completed = updates.completed
    if updates.due_date is not None:
        task.due_date = updates.due_date

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, owner_id: int, task_id: int) -> bool:
    task = get_task(db, owner_id, task_id)
    if not task:
        return False

    db.delete(task)
    db.commit()
    return True
