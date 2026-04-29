# app/main.py
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .deps import get_db, get_current_user
from .auth import create_access_token

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
    task, error = crud.create_task(db, current_user.id, task_in)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return task


@app.get("/tasks", response_model=list[schemas.TaskOut])
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
    task, error = crud.update_task(db, current_user.id, task_id, updates)
    if error == "Task not found":
        raise HTTPException(status_code=404, detail=error)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ok, error = crud.delete_task(db, current_user.id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail=error)
    return None


# =====================
# BATCH OPERATIONS
# =====================

@app.post("/tasks/batch/update", response_model=schemas.BatchUpdateResponse)
def batch_update_tasks(
    request: schemas.BatchUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not request.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")
    
    successes, failures = crud.batch_update_tasks(
        db,
        current_user.id,
        request.task_ids,
        request.updates
    )
    
    return schemas.BatchUpdateResponse(
        total=len(request.task_ids),
        success_count=len(successes),
        failure_count=len(failures),
        successes=successes,
        failures=failures
    )


@app.post("/tasks/batch/delete", response_model=schemas.BatchDeleteResponse)
def batch_delete_tasks(
    request: schemas.BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not request.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")
    
    successes, failures = crud.batch_delete_tasks(
        db,
        current_user.id,
        request.task_ids
    )
    
    return schemas.BatchDeleteResponse(
        total=len(request.task_ids),
        success_count=len(successes),
        failure_count=len(failures),
        successes=successes,
        failures=failures
    )