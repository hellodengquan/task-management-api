# app/crud.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

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
# TAGS
# =====================

def get_tag_by_name(db: Session, owner_id: int, name: str):
    return (
        db.query(models.Tag)
        .filter(models.Tag.owner_id == owner_id, models.Tag.name == name)
        .first()
    )


def get_tag(db: Session, owner_id: int, tag_id: int):
    return (
        db.query(models.Tag)
        .filter(models.Tag.owner_id == owner_id, models.Tag.id == tag_id)
        .first()
    )


def list_tags(db: Session, owner_id: int):
    return (
        db.query(models.Tag)
        .filter(models.Tag.owner_id == owner_id)
        .order_by(models.Tag.name)
        .all()
    )


def create_tag(db: Session, owner_id: int, tag_in: schemas.TagCreate):
    existing = get_tag_by_name(db, owner_id, tag_in.name)
    if existing:
        return None

    tag = models.Tag(
        name=tag_in.name,
        color=tag_in.color,
        owner_id=owner_id,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, owner_id: int, tag_id: int, updates: schemas.TagUpdate):
    tag = get_tag(db, owner_id, tag_id)
    if not tag:
        return None

    if updates.name is not None:
        if updates.name != tag.name:
            existing = get_tag_by_name(db, owner_id, updates.name)
            if existing:
                return None
        tag.name = updates.name
    if updates.color is not None:
        tag.color = updates.color

    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, owner_id: int, tag_id: int) -> bool:
    tag = get_tag(db, owner_id, tag_id)
    if not tag:
        return False

    db.delete(tag)
    db.commit()
    return True


def get_tags_by_ids(db: Session, owner_id: int, tag_ids: List[int]) -> List[models.Tag]:
    if not tag_ids:
        return []
    return (
        db.query(models.Tag)
        .filter(models.Tag.owner_id == owner_id, models.Tag.id.in_(tag_ids))
        .all()
    )


# =====================
# TASKS
# =====================

def create_task(db: Session, owner_id: int, task_in: schemas.TaskCreate):
    task = models.Task(
        title=task_in.title,
        description=task_in.description,
        owner_id=owner_id,
    )

    if task_in.tag_ids:
        tags = get_tags_by_ids(db, owner_id, task_in.tag_ids)
        task.tags = tags

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, owner_id: int, tag_ids: Optional[List[int]] = None):
    query = db.query(models.Task).filter(models.Task.owner_id == owner_id)

    if tag_ids:
        task_tags_subquery = (
            select(models.task_tags.c.task_id)
            .where(models.task_tags.c.tag_id.in_(tag_ids))
            .group_by(models.task_tags.c.task_id)
            .having(func.count(models.task_tags.c.tag_id) == len(tag_ids))
        )
        query = query.filter(models.Task.id.in_(task_tags_subquery))

    return query.order_by(models.Task.created_at.desc()).all()


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
    if updates.tag_ids is not None:
        tags = get_tags_by_ids(db, owner_id, updates.tag_ids)
        task.tags = tags

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
