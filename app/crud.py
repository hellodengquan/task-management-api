# app/crud.py
from typing import Any
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import hash_password, verify_password
from .models import ActionType


def _create_history_record(
    db: Session,
    task_id: int,
    user_id: int,
    action: ActionType,
    details: dict[str, Any] | None = None,
):
    history = models.TaskHistory(
        task_id=task_id,
        user_id=user_id,
        action=action,
        details=details,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def _get_task_changes(
    old_task: models.Task,
    updates: schemas.TaskUpdate,
) -> dict[str, Any]:
    changes = {}
    if updates.title is not None and old_task.title != updates.title:
        changes["title"] = {"old": old_task.title, "new": updates.title}
    if updates.description is not None and old_task.description != updates.description:
        changes["description"] = {"old": old_task.description, "new": updates.description}
    if updates.completed is not None and old_task.completed != updates.completed:
        changes["completed"] = {"old": old_task.completed, "new": updates.completed}
    return changes


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
# TASKS
# =====================

def create_task(db: Session, owner_id: int, task_in: schemas.TaskCreate):
    task = models.Task(
        title=task_in.title,
        description=task_in.description,
        owner_id=owner_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    _create_history_record(
        db=db,
        task_id=task.id,
        user_id=owner_id,
        action=ActionType.CREATE,
        details={
            "title": task_in.title,
            "description": task_in.description,
        },
    )

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

    changes = _get_task_changes(task, updates)

    if updates.title is not None:
        task.title = updates.title
    if updates.description is not None:
        task.description = updates.description
    if updates.completed is not None:
        task.completed = updates.completed

    db.commit()
    db.refresh(task)

    if changes:
        _create_history_record(
            db=db,
            task_id=task_id,
            user_id=owner_id,
            action=ActionType.UPDATE,
            details=changes,
        )

    return task


def delete_task(db: Session, owner_id: int, task_id: int) -> bool:
    task = get_task(db, owner_id, task_id)
    if not task:
        return False

    _create_history_record(
        db=db,
        task_id=task_id,
        user_id=owner_id,
        action=ActionType.DELETE,
        details={
            "title": task.title,
            "description": task.description,
            "completed": task.completed,
        },
    )

    db.delete(task)
    db.commit()
    return True


# =====================
# TASK HISTORY
# =====================

def get_task_history(db: Session, task_id: int):
    return (
        db.query(models.TaskHistory)
        .filter(models.TaskHistory.task_id == task_id)
        .order_by(models.TaskHistory.created_at.asc())
        .all()
    )


def get_task_history_with_owner_check(db: Session, owner_id: int, task_id: int):
    task = get_task(db, owner_id, task_id)
    if task:
        return get_task_history(db, task_id)

    history = (
        db.query(models.TaskHistory)
        .filter(
            models.TaskHistory.task_id == task_id,
            models.TaskHistory.user_id == owner_id,
        )
        .order_by(models.TaskHistory.created_at.asc())
        .all()
    )

    if history:
        return history

    return None
