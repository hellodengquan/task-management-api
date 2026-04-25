# app/crud.py
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import hash_password, verify_password


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


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def list_users(db: Session):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


def update_user_role(db: Session, user_id: int, role: schemas.Role):
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    user.role = role.value
    db.commit()
    db.refresh(user)
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
    return task


def list_tasks(db: Session, owner_id: int, is_admin: bool = False):
    query = db.query(models.Task)
    if not is_admin:
        query = query.filter(models.Task.owner_id == owner_id)
    return query.order_by(models.Task.created_at.desc()).all()


def get_task(db: Session, owner_id: int, task_id: int, is_admin: bool = False):
    query = db.query(models.Task).filter(models.Task.id == task_id)
    if not is_admin:
        query = query.filter(models.Task.owner_id == owner_id)
    return query.first()


def update_task(db: Session, owner_id: int, task_id: int, updates: schemas.TaskUpdate, is_admin: bool = False):
    task = get_task(db, owner_id, task_id, is_admin)
    if not task:
        return None

    if updates.title is not None:
        task.title = updates.title
    if updates.description is not None:
        task.description = updates.description
    if updates.completed is not None:
        task.completed = updates.completed

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, owner_id: int, task_id: int, is_admin: bool = False) -> bool:
    task = get_task(db, owner_id, task_id, is_admin)
    if not task:
        return False

    db.delete(task)
    db.commit()
    return True
