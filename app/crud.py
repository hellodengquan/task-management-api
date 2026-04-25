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


# =====================
# COMMENTS
# =====================

def create_comment(db: Session, task_id: int, author_id: int, comment_in: schemas.CommentCreate):
    comment = models.Comment(
        content=comment_in.content,
        task_id=task_id,
        author_id=author_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_task_comments(db: Session, task_id: int, skip: int = 0, limit: int = 20):
    return (
        db.query(models.Comment)
        .filter(models.Comment.task_id == task_id)
        .order_by(models.Comment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_task_comments(db: Session, task_id: int) -> int:
    return (
        db.query(models.Comment)
        .filter(models.Comment.task_id == task_id)
        .count()
    )


def get_comment(db: Session, comment_id: int):
    return (
        db.query(models.Comment)
        .filter(models.Comment.id == comment_id)
        .first()
    )


def update_comment(db: Session, comment_id: int, updates: schemas.CommentUpdate):
    comment = get_comment(db, comment_id)
    if not comment:
        return None

    if updates.content is not None:
        comment.content = updates.content

    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment_id: int) -> bool:
    comment = get_comment(db, comment_id)
    if not comment:
        return False

    db.delete(comment)
    db.commit()
    return True
