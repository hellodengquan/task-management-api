# app/main.py
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .deps import get_db, get_current_user
from .auth import create_access_token

app = FastAPI(title="Task Management API")


def task_to_out(task: models.Task, db: Session) -> schemas.TaskOut:
    progress = crud.calculate_task_progress(db, task)
    return schemas.TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        completed=task.completed,
        created_at=task.created_at,
        updated_at=task.updated_at,
        parent_id=task.parent_id,
        progress=progress,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# =====================
# AUTH
# =====================

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    user = crud.create_user(db, user_in)
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Put user id in "sub" (subject)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


# =====================
# TASKS
# =====================

@app.post("/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(
    task_in: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = crud.create_task(db, current_user.id, task_in)
    if not task:
        raise HTTPException(status_code=400, detail="Invalid parent task")
    return task_to_out(task, db)


@app.get("/tasks", response_model=list[schemas.TaskOut])
def get_tasks(
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tasks = crud.list_tasks(db, current_user.id, parent_id)
    return [task_to_out(task, db) for task in tasks]


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = crud.get_task(db, current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_out(task, db)


@app.get("/tasks/{task_id}/subtasks", response_model=list[schemas.TaskOut])
def get_subtasks(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    parent_task = crud.get_task(db, current_user.id, task_id)
    if not parent_task:
        raise HTTPException(status_code=404, detail="Task not found")

    subtasks = crud.get_all_subtasks(db, current_user.id, task_id)
    if subtasks is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return [task_to_out(task, db) for task in subtasks]


@app.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def patch_task(
    task_id: int,
    updates: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = crud.update_task(db, current_user.id, task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or invalid parent")
    return task_to_out(task, db)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ok = crud.delete_task(db, current_user.id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return None
