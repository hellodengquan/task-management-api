# app/crud.py
from typing import List, Tuple
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import hash_password, verify_password
from .models import TaskStatus


# =====================
# USERS
# =====================

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


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
    if task_in.assignee_id is not None:
        assignee = get_user_by_id(db, task_in.assignee_id)
        if not assignee:
            return None, "Assignee not found"

    task = models.Task(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        priority=task_in.priority,
        assignee_id=task_in.assignee_id,
        owner_id=owner_id,
    )
    if task.status == TaskStatus.COMPLETED:
        task.completed = True
    db.add(task)
    db.commit()
    db.refresh(task)
    return task, None


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


def get_tasks_by_ids(db: Session, owner_id: int, task_ids: List[int]):
    return (
        db.query(models.Task)
        .filter(models.Task.owner_id == owner_id, models.Task.id.in_(task_ids))
        .all()
    )


def update_task(db: Session, owner_id: int, task_id: int, updates: schemas.TaskUpdate):
    task = get_task(db, owner_id, task_id)
    if not task:
        return None, "Task not found"

    if updates.assignee_id is not None:
        assignee = get_user_by_id(db, updates.assignee_id)
        if not assignee:
            return None, "Assignee not found"

    if updates.title is not None:
        task.title = updates.title
    if updates.description is not None:
        task.description = updates.description
    if updates.completed is not None:
        task.completed = updates.completed
        if updates.completed:
            task.status = TaskStatus.COMPLETED
    if updates.status is not None:
        task.status = updates.status
        if updates.status == TaskStatus.COMPLETED:
            task.completed = True
        else:
            task.completed = False
    if updates.priority is not None:
        task.priority = updates.priority
    if updates.assignee_id is not None:
        task.assignee_id = updates.assignee_id

    db.commit()
    db.refresh(task)
    return task, None


def delete_task(db: Session, owner_id: int, task_id: int) -> Tuple[bool, str]:
    task = get_task(db, owner_id, task_id)
    if not task:
        return False, "Task not found"

    db.delete(task)
    db.commit()
    return True, None


# =====================
# BATCH OPERATIONS
# =====================

def batch_update_tasks(
    db: Session,
    owner_id: int,
    task_ids: List[int],
    updates: schemas.TaskUpdate
):
    successes = []
    failures = []
    
    if updates.assignee_id is not None:
        assignee = get_user_by_id(db, updates.assignee_id)
        if not assignee:
            for task_id in task_ids:
                failures.append(schemas.BatchOperationResult(
                    success=False,
                    task_id=task_id,
                    detail="Assignee not found"
                ))
            return successes, failures

    existing_tasks = get_tasks_by_ids(db, owner_id, task_ids)
    existing_task_map = {task.id: task for task in existing_tasks}
    
    for task_id in task_ids:
        if task_id not in existing_task_map:
            failures.append(schemas.BatchOperationResult(
                success=False,
                task_id=task_id,
                detail="Task not found"
            ))
            continue
        
        task = existing_task_map[task_id]
        
        if updates.title is not None:
            task.title = updates.title
        if updates.description is not None:
            task.description = updates.description
        if updates.completed is not None:
            task.completed = updates.completed
            if updates.completed:
                task.status = TaskStatus.COMPLETED
        if updates.status is not None:
            task.status = updates.status
            if updates.status == TaskStatus.COMPLETED:
                task.completed = True
            else:
                task.completed = False
        if updates.priority is not None:
            task.priority = updates.priority
        if updates.assignee_id is not None:
            task.assignee_id = updates.assignee_id
        
        successes.append(task)
    
    if successes:
        db.commit()
        for task in successes:
            db.refresh(task)
    
    return successes, failures


def batch_delete_tasks(db: Session, owner_id: int, task_ids: List[int]):
    successes = []
    failures = []
    
    existing_tasks = get_tasks_by_ids(db, owner_id, task_ids)
    existing_task_map = {task.id: task for task in existing_tasks}
    
    for task_id in task_ids:
        if task_id not in existing_task_map:
            failures.append(schemas.BatchOperationResult(
                success=False,
                task_id=task_id,
                detail="Task not found"
            ))
            continue
        
        task = existing_task_map[task_id]
        db.delete(task)
        successes.append(schemas.BatchOperationResult(
            success=True,
            task_id=task_id,
            detail=None
        ))
    
    if successes:
        db.commit()
    
    return successes, failures