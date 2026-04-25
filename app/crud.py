# app/crud.py
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .auth import hash_password, verify_password


def calculate_task_progress(db: Session, task: models.Task) -> float:
    all_tasks = []
    completed_count = 0

    stack = [task]
    while stack:
        current = stack.pop()
        db.refresh(current, ['children'])
        all_tasks.append(current)
        for child in current.children:
            stack.append(child)

    for t in all_tasks:
        if t.completed:
            completed_count += 1

    if len(all_tasks) == 0:
        return 0.0

    return (completed_count / len(all_tasks)) * 100.0


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
    if task_in.parent_id is not None:
        parent_task = get_task(db, owner_id, task_in.parent_id)
        if not parent_task:
            return None

    task = models.Task(
        title=task_in.title,
        description=task_in.description,
        owner_id=owner_id,
        parent_id=task_in.parent_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, owner_id: int, parent_id: int = None):
    query = (
        db.query(models.Task)
        .filter(models.Task.owner_id == owner_id)
    )

    if parent_id is not None:
        query = query.filter(models.Task.parent_id == parent_id)

    return query.order_by(models.Task.created_at.desc()).all()


def get_task(db: Session, owner_id: int, task_id: int):
    return (
        db.query(models.Task)
        .filter(models.Task.owner_id == owner_id, models.Task.id == task_id)
        .first()
    )


def get_task_with_children(db: Session, owner_id: int, task_id: int):
    return (
        db.query(models.Task)
        .options(joinedload(models.Task.children))
        .filter(models.Task.owner_id == owner_id, models.Task.id == task_id)
        .first()
    )


def get_all_subtasks(db: Session, owner_id: int, parent_task_id: int):
    parent_task = get_task(db, owner_id, parent_task_id)
    if not parent_task:
        return None

    all_subtasks = []
    stack = [parent_task]
    visited = {parent_task_id}

    while stack:
        current = stack.pop()
        db.refresh(current, ['children'])

        for child in current.children:
            if child.id not in visited:
                visited.add(child.id)
                all_subtasks.append(child)
                stack.append(child)

    return all_subtasks


def update_task(db: Session, owner_id: int, task_id: int, updates: schemas.TaskUpdate):
    task = get_task(db, owner_id, task_id)
    if not task:
        return None

    if updates.parent_id is not None:
        if updates.parent_id == task_id:
            return None

        parent_task = get_task(db, owner_id, updates.parent_id)
        if not parent_task:
            return None

        all_subtasks = get_all_subtasks(db, owner_id, task_id)
        if all_subtasks is not None:
            for subtask in all_subtasks:
                if subtask.id == updates.parent_id:
                    return None

    if updates.title is not None:
        task.title = updates.title
    if updates.description is not None:
        task.description = updates.description
    if updates.completed is not None:
        task.completed = updates.completed
    if updates.parent_id is not None:
        task.parent_id = updates.parent_id

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
