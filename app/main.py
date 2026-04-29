# app/main.py
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .deps import get_db, get_current_user
from .auth import create_access_token
from .recurrence import generate_due_tasks, generate_tasks_for_plan

app = FastAPI(title="Task Management API")


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
    if task_in.recurrence_plan_id is not None:
        plan = crud.get_recurrence_plan(db, current_user.id, task_in.recurrence_plan_id)
        if not plan:
            raise HTTPException(status_code=400, detail="Invalid recurrence plan ID")
    
    return crud.create_task(db, current_user.id, task_in)


@app.get("/tasks", response_model=List[schemas.TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.list_tasks(db, current_user.id)


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = crud.get_task(db, current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def patch_task(
    task_id: int,
    updates: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = crud.update_task(db, current_user.id, task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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


# =====================
# RECURRENCE PLANS
# =====================

@app.post("/recurrence-plans", response_model=schemas.RecurrencePlanOut, status_code=201)
def create_recurrence_plan(
    plan_in: schemas.RecurrencePlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_recurrence_plan(db, current_user.id, plan_in)


@app.get("/recurrence-plans", response_model=List[schemas.RecurrencePlanOut])
def get_recurrence_plans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.list_recurrence_plans(db, current_user.id)


@app.get("/recurrence-plans/{plan_id}", response_model=schemas.RecurrencePlanOut)
def get_recurrence_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = crud.get_recurrence_plan(db, current_user.id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Recurrence plan not found")
    return plan


@app.patch("/recurrence-plans/{plan_id}", response_model=schemas.RecurrencePlanOut)
def patch_recurrence_plan(
    plan_id: int,
    updates: schemas.RecurrencePlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = crud.update_recurrence_plan(db, current_user.id, plan_id, updates)
    if not plan:
        raise HTTPException(status_code=404, detail="Recurrence plan not found")
    return plan


@app.delete("/recurrence-plans/{plan_id}", status_code=204)
def delete_recurrence_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ok = crud.delete_recurrence_plan(db, current_user.id, plan_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Recurrence plan not found")
    return None


# =====================
# SKIPPED OCCURRENCES
# =====================

@app.post(
    "/recurrence-plans/{plan_id}/skipped-occurrences",
    response_model=schemas.SkippedOccurrenceOut,
    status_code=201
)
def create_skipped_occurrence(
    plan_id: int,
    occurrence_in: schemas.SkippedOccurrenceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = crud.get_recurrence_plan(db, current_user.id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Recurrence plan not found")
    
    return crud.create_skipped_occurrence(db, plan_id, occurrence_in)


@app.get(
    "/recurrence-plans/{plan_id}/skipped-occurrences",
    response_model=List[schemas.SkippedOccurrenceOut]
)
def get_skipped_occurrences(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = crud.get_recurrence_plan(db, current_user.id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Recurrence plan not found")
    
    return crud.list_skipped_occurrences(db, plan_id)


# =====================
# TASK GENERATION
# =====================

@app.post("/recurrence-plans/generate-due-tasks", response_model=List[schemas.TaskOut])
def trigger_generate_due_tasks(
    current_time: datetime = Query(None, description="Optional current time for testing"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tasks = generate_due_tasks(db, current_time)
    return tasks


@app.post("/recurrence-plans/{plan_id}/generate-tasks", response_model=List[schemas.TaskOut])
def trigger_generate_tasks_for_plan(
    plan_id: int,
    current_time: datetime = Query(None, description="Optional current time for testing"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = crud.get_recurrence_plan(db, current_user.id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Recurrence plan not found")
    
    tasks = generate_tasks_for_plan(db, plan, current_time)
    return tasks
