# app/recurrence.py
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, crud, schemas
from .models import RecurrenceFrequency


def calculate_next_occurrence(
    plan: models.RecurrencePlan,
    from_date: datetime = None
) -> Optional[datetime]:
    """
    Calculate the next occurrence date based on the recurrence plan.
    """
    if from_date is None:
        from_date = plan.last_generated or datetime.utcnow()
    
    # Normalize from_date to start of day
    from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if plan.frequency == RecurrenceFrequency.DAILY:
        return _calculate_daily_next(plan, from_date)
    elif plan.frequency == RecurrenceFrequency.WEEKLY:
        return _calculate_weekly_next(plan, from_date)
    elif plan.frequency == RecurrenceFrequency.MONTHLY:
        return _calculate_monthly_next(plan, from_date)
    elif plan.frequency == RecurrenceFrequency.YEARLY:
        return _calculate_yearly_next(plan, from_date)
    
    return None


def _calculate_daily_next(plan: models.RecurrencePlan, from_date: datetime) -> datetime:
    return from_date + timedelta(days=plan.interval)


def _calculate_weekly_next(plan: models.RecurrencePlan, from_date: datetime) -> Optional[datetime]:
    week_days = crud.comma_string_to_list(plan.week_days)
    
    if not week_days:
        return from_date + timedelta(weeks=plan.interval)
    
    current_weekday = from_date.weekday()  # 0=Monday, 6=Sunday
    
    sorted_days = sorted(week_days)
    next_day = None
    
    for day in sorted_days:
        if day > current_weekday:
            next_day = day
            break
    
    if next_day is None:
        next_day = sorted_days[0]
        weeks_to_add = plan.interval
    else:
        weeks_to_add = 0 if next_day > current_weekday else plan.interval
    
    days_diff = (next_day - current_weekday) + (weeks_to_add * 7)
    return from_date + timedelta(days=days_diff)


def _calculate_monthly_next(plan: models.RecurrencePlan, from_date: datetime) -> Optional[datetime]:
    month_days = crud.comma_string_to_list(plan.month_days)
    
    if not month_days:
        months_to_add = plan.interval
        new_month = from_date.month + months_to_add
        new_year = from_date.year + (new_month - 1) // 12
        new_month = (new_month - 1) % 12 + 1
        
        max_day = _get_days_in_month(new_year, new_month)
        day = min(from_date.day, max_day)
        
        return datetime(new_year, new_month, day)
    
    sorted_days = sorted(month_days)
    current_day = from_date.day
    next_day = None
    
    for day in sorted_days:
        if day > current_day:
            max_day = _get_days_in_month(from_date.year, from_date.month)
            if day <= max_day:
                next_day = day
                break
    
    if next_day is not None:
        return datetime(from_date.year, from_date.month, next_day)
    
    next_month = from_date.month + plan.interval
    next_year = from_date.year + (next_month - 1) // 12
    next_month = (next_month - 1) % 12 + 1
    
    max_day = _get_days_in_month(next_year, next_month)
    next_day = min(sorted_days[0], max_day)
    
    return datetime(next_year, next_month, next_day)


def _calculate_yearly_next(plan: models.RecurrencePlan, from_date: datetime) -> datetime:
    years_to_add = plan.interval
    new_year = from_date.year + years_to_add
    
    max_day = _get_days_in_month(new_year, from_date.month)
    day = min(from_date.day, max_day)
    
    return datetime(new_year, from_date.month, day)


def _get_days_in_month(year: int, month: int) -> int:
    if month == 2:
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 29
        return 28
    elif month in [4, 6, 9, 11]:
        return 30
    return 31


def _get_start_date_for_plan(plan: models.RecurrencePlan, current_time: datetime) -> datetime:
    """
    Determine the start date for generating tasks when last_generated is None.
    """
    base_date = plan.created_at if plan.created_at else current_time
    base_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if plan.frequency == RecurrenceFrequency.DAILY:
        return base_date - timedelta(days=plan.interval)
    elif plan.frequency == RecurrenceFrequency.WEEKLY:
        return base_date - timedelta(weeks=plan.interval)
    elif plan.frequency == RecurrenceFrequency.MONTHLY:
        months_back = plan.interval
        new_month = base_date.month - months_back
        new_year = base_date.year
        while new_month <= 0:
            new_month += 12
            new_year -= 1
        max_day = _get_days_in_month(new_year, new_month)
        day = min(base_date.day, max_day)
        return datetime(new_year, new_month, day)
    elif plan.frequency == RecurrenceFrequency.YEARLY:
        return datetime(
            base_date.year - plan.interval,
            base_date.month,
            min(base_date.day, _get_days_in_month(base_date.year - plan.interval, base_date.month))
        )
    
    return base_date


def generate_tasks_for_plan(
    db: Session,
    plan: models.RecurrencePlan,
    current_time: datetime = None
) -> List[models.Task]:
    """
    Generate new tasks for a recurrence plan if needed.
    """
    if current_time is None:
        current_time = datetime.utcnow()
    
    if not plan.is_active:
        return []
    
    if plan.end_date and current_time > plan.end_date:
        return []
    
    generated_tasks = []
    last_generated = plan.last_generated
    
    if last_generated is None:
        start_date = _get_start_date_for_plan(plan, current_time)
        next_occurrence = calculate_next_occurrence(plan, start_date)
    else:
        next_occurrence = calculate_next_occurrence(plan, last_generated)
    
    while next_occurrence and next_occurrence <= current_time:
        if plan.end_date and next_occurrence > plan.end_date:
            break
        
        if not crud.is_occurrence_skipped(db, plan.id, next_occurrence):
            first_task = db.query(models.Task).filter(
                models.Task.recurrence_plan_id == plan.id
            ).order_by(models.Task.created_at.asc()).first()
            
            if first_task:
                task_title = first_task.title
                task_description = first_task.description
            else:
                task_title = f"Recurring Task (Plan {plan.id})"
                task_description = None
            
            task_in = schemas.TaskCreate(
                title=task_title,
                description=task_description,
                due_date=next_occurrence,
                recurrence_plan_id=plan.id,
            )
            task = crud.create_task(db, plan.owner_id, task_in)
            generated_tasks.append(task)
        
        plan.last_generated = next_occurrence
        db.commit()
        
        next_occurrence = calculate_next_occurrence(plan, next_occurrence)
    
    return generated_tasks


def generate_due_tasks(db: Session, current_time: datetime = None) -> List[models.Task]:
    """
    Generate all due tasks for active recurrence plans.
    """
    if current_time is None:
        current_time = datetime.utcnow()
    
    active_plans = db.query(models.RecurrencePlan).filter(
        models.RecurrencePlan.is_active == True
    ).all()
    
    all_generated_tasks = []
    for plan in active_plans:
        if plan.end_date and current_time > plan.end_date:
            continue
        
        tasks = generate_tasks_for_plan(db, plan, current_time)
        all_generated_tasks.extend(tasks)
    
    return all_generated_tasks