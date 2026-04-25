# app/main.py
from fastapi import Depends, FastAPI, HTTPException, Query, status
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
    return crud.create_task(db, current_user.id, task_in)


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
# COMMENTS
# =====================

@app.post("/tasks/{task_id}/comments", response_model=schemas.CommentOut, status_code=201)
def create_comment(
    task_id: int,
    comment_in: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 验证任务是否存在
    task = crud.get_task(db, current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud.create_comment(db, task_id, current_user.id, comment_in)


@app.get("/tasks/{task_id}/comments", response_model=schemas.CommentPaginationOut)
def get_task_comments(
    task_id: int,
    skip: int = Query(0, ge=0, description="跳过多少条记录"),
    limit: int = Query(20, ge=1, le=100, description="返回多少条记录（最大100）"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 验证任务是否存在
    task = crud.get_task(db, current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    comments = crud.get_task_comments(db, task_id, skip=skip, limit=limit)
    total = crud.count_task_comments(db, task_id)
    
    return {
        "items": comments,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.patch("/comments/{comment_id}", response_model=schemas.CommentOut)
def patch_comment(
    comment_id: int,
    updates: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 验证评论是否存在
    comment = crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 验证是否是评论作者
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    updated_comment = crud.update_comment(db, comment_id, updates)
    if not updated_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return updated_comment


@app.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 验证评论是否存在
    comment = crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 验证是否是评论作者
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    ok = crud.delete_comment(db, comment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Comment not found")
    return None
