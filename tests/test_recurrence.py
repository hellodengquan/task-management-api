from datetime import datetime, timedelta
import pytest


def register_and_login(client, email, password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================
# RECURRENCE PLANS TESTS
# =====================

def test_create_recurrence_plan_requires_auth(client):
    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1
        }
    )

    assert response.status_code == 401


def test_create_recurrence_plan_success(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["frequency"] == "daily"
    assert data["interval"] == 1
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


def test_create_recurrence_plan_with_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "weekly",
            "interval": 1,
            "week_days": [0, 2, 4],  # Monday, Wednesday, Friday
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["frequency"] == "weekly"
    assert data["week_days"] == [0, 2, 4]


def test_list_recurrence_plans(client):
    headers = register_and_login(client, "user1@example.com")

    client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1},
        headers=headers
    )
    client.post(
        "/recurrence-plans",
        json={"frequency": "weekly", "interval": 2},
        headers=headers
    )

    response = client.get("/recurrence-plans", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_recurrence_plan(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={"frequency": "monthly", "interval": 1},
        headers=headers
    )

    plan_id = create_response.json()["id"]

    response = client.get(f"/recurrence-plans/{plan_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["frequency"] == "monthly"


def test_cannot_get_another_users_plan(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1},
        headers=headers1
    )

    plan_id = create_response.json()["id"]

    response = client.get(f"/recurrence-plans/{plan_id}", headers=headers2)

    assert response.status_code == 404


def test_update_recurrence_plan(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1, "is_active": True},
        headers=headers
    )

    plan_id = create_response.json()["id"]

    response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={"interval": 2, "is_active": False},
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["interval"] == 2
    assert data["is_active"] is False


def test_delete_recurrence_plan(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1},
        headers=headers
    )

    plan_id = create_response.json()["id"]

    delete_response = client.delete(f"/recurrence-plans/{plan_id}", headers=headers)

    assert delete_response.status_code == 204

    get_response = client.get(f"/recurrence-plans/{plan_id}", headers=headers)

    assert get_response.status_code == 404


# =====================
# SKIPPED OCCURRENCES TESTS
# =====================

def test_create_skipped_occurrence(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]
    occurrence_date = (datetime.now() + timedelta(days=1)).isoformat()

    response = client.post(
        f"/recurrence-plans/{plan_id}/skipped-occurrences",
        json={
            "occurrence_date": occurrence_date,
            "reason": "Vacation"
        },
        headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reason"] == "Vacation"
    assert "occurrence_date" in data


def test_list_skipped_occurrences(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    date1 = (datetime.now() + timedelta(days=1)).isoformat()
    date2 = (datetime.now() + timedelta(days=2)).isoformat()

    client.post(
        f"/recurrence-plans/{plan_id}/skipped-occurrences",
        json={"occurrence_date": date1},
        headers=headers
    )
    client.post(
        f"/recurrence-plans/{plan_id}/skipped-occurrences",
        json={"occurrence_date": date2},
        headers=headers
    )

    response = client.get(
        f"/recurrence-plans/{plan_id}/skipped-occurrences",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


# =====================
# TASK GENERATION TESTS
# =====================

def test_generate_daily_tasks(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1, "is_active": True},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    client.post(
        "/tasks",
        json={
            "title": "Daily Task",
            "description": "This is a daily task",
            "recurrence_plan_id": plan_id
        },
        headers=headers
    )

    current_time = datetime.now()
    past_time = current_time - timedelta(days=3)

    response = client.post(
        f"/recurrence-plans/{plan_id}/generate-tasks?current_time={past_time.isoformat()}",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # No tasks should be generated for past time when last_generated is None

    tasks_response = client.get("/tasks", headers=headers)
    initial_tasks = tasks_response.json()
    assert len(initial_tasks) == 1  # Only the manually created task

    future_time = current_time + timedelta(days=1)

    response2 = client.post(
        f"/recurrence-plans/{plan_id}/generate-tasks?current_time={future_time.isoformat()}",
        headers=headers
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) >= 1  # Should generate at least one task


def test_skipped_occurrence_not_generated(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1, "is_active": True},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    client.post(
        "/tasks",
        json={
            "title": "Daily Task",
            "recurrence_plan_id": plan_id
        },
        headers=headers
    )

    skip_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    client.post(
        f"/recurrence-plans/{plan_id}/skipped-occurrences",
        json={
            "occurrence_date": skip_date.isoformat(),
            "reason": "Skip this one"
        },
        headers=headers
    )

    future_time = skip_date + timedelta(hours=12)

    response = client.post(
        f"/recurrence-plans/{plan_id}/generate-tasks?current_time={future_time.isoformat()}",
        headers=headers
    )

    assert response.status_code == 200

    tasks = response.json()
    
    skipped_task_found = any(
        task.get("due_date") and 
        datetime.fromisoformat(task["due_date"].replace("Z", "+00:00")).date() == skip_date.date()
        for task in tasks
    )
    
    assert not skipped_task_found, "Skipped occurrence should not generate a task"


def test_inactive_plan_does_not_generate_tasks(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1, "is_active": False},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    future_time = datetime.now() + timedelta(days=1)

    response = client.post(
        f"/recurrence-plans/{plan_id}/generate-tasks?current_time={future_time.isoformat()}",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Inactive plan should not generate tasks


def test_plan_with_end_date(client):
    headers = register_and_login(client, "user1@example.com")

    end_date = datetime.now() + timedelta(days=5)

    create_plan_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True,
            "end_date": end_date.isoformat()
        },
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    after_end_date = end_date + timedelta(days=10)

    response = client.post(
        f"/recurrence-plans/{plan_id}/generate-tasks?current_time={after_end_date.isoformat()}",
        headers=headers
    )

    assert response.status_code == 200
    # Tasks should not be generated after end_date


# =====================
# TASK WITH RECURRENCE PLAN
# =====================

def test_create_task_with_invalid_plan_id(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks",
        json={
            "title": "Test Task",
            "recurrence_plan_id": 999999
        },
        headers=headers
    )

    assert response.status_code == 400
    assert "Invalid recurrence plan ID" in response.json()["detail"]


def test_create_task_with_valid_plan_id(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "weekly", "interval": 1},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    response = client.post(
        "/tasks",
        json={
            "title": "Weekly Report",
            "description": "Write weekly report",
            "recurrence_plan_id": plan_id
        },
        headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["recurrence_plan_id"] == plan_id


# =====================
# SECURITY TESTS
# =====================

def test_batch_generate_only_processes_own_plans(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_plan_response1 = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1, "is_active": True},
        headers=headers1
    )
    plan_id1 = create_plan_response1.json()["id"]

    client.post(
        "/tasks",
        json={
            "title": "User1 Daily Task",
            "recurrence_plan_id": plan_id1
        },
        headers=headers1
    )

    create_plan_response2 = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1, "is_active": True},
        headers=headers2
    )
    plan_id2 = create_plan_response2.json()["id"]

    client.post(
        "/tasks",
        json={
            "title": "User2 Daily Task",
            "recurrence_plan_id": plan_id2
        },
        headers=headers2
    )

    future_time = datetime.now() + timedelta(days=1)

    tasks_before_user1 = client.get("/tasks", headers=headers1).json()
    tasks_before_user2 = client.get("/tasks", headers=headers2).json()

    client.post(
        f"/recurrence-plans/generate-due-tasks?current_time={future_time.isoformat()}",
        headers=headers1
    )

    tasks_after_user1 = client.get("/tasks", headers=headers1).json()
    tasks_after_user2 = client.get("/tasks", headers=headers2).json()

    assert len(tasks_after_user1) > len(tasks_before_user1)
    assert len(tasks_after_user2) == len(tasks_before_user2)


# =====================
# VALIDATION TESTS
# =====================

def test_week_days_invalid_value(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "weekly",
            "interval": 1,
            "week_days": [0, 7],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "week_days must be between 0 and 6" in response.json()["detail"][0]["msg"]


def test_month_days_invalid_value(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "monthly",
            "interval": 1,
            "month_days": [0, 15],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "month_days must be between 1 and 31" in response.json()["detail"][0]["msg"]


def test_month_days_invalid_value_32(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "monthly",
            "interval": 1,
            "month_days": [32],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "month_days must be between 1 and 31" in response.json()["detail"][0]["msg"]


def test_daily_cannot_have_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "week_days": [0, 1],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "week_days is not allowed for daily frequency" in response.json()["detail"][0]["msg"]


def test_daily_cannot_have_month_days(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "month_days": [1, 15],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "month_days is not allowed for daily frequency" in response.json()["detail"][0]["msg"]


def test_weekly_cannot_have_month_days(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "weekly",
            "interval": 1,
            "week_days": [0, 2],
            "month_days": [1],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "month_days is not allowed for weekly frequency" in response.json()["detail"][0]["msg"]


def test_monthly_cannot_have_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "monthly",
            "interval": 1,
            "week_days": [0],
            "month_days": [1],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "week_days is not allowed for monthly frequency" in response.json()["detail"][0]["msg"]


def test_yearly_cannot_have_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "yearly",
            "interval": 1,
            "week_days": [0],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "week_days is not allowed for yearly frequency" in response.json()["detail"][0]["msg"]


def test_yearly_cannot_have_month_days(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "yearly",
            "interval": 1,
            "month_days": [1],
            "is_active": True
        },
        headers=headers
    )

    assert response.status_code == 422
    assert "month_days is not allowed for yearly frequency" in response.json()["detail"][0]["msg"]


# =====================
# SKIP DATE NORMALIZATION TESTS
# =====================

def test_skip_occurrence_matches_any_time_on_same_day(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1, "is_active": True},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    client.post(
        "/tasks",
        json={
            "title": "Daily Task",
            "recurrence_plan_id": plan_id
        },
        headers=headers
    )

    skip_date_morning = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    skip_date_afternoon = datetime.now().replace(hour=14, minute=30, second=0, microsecond=0) + timedelta(days=1)

    client.post(
        f"/recurrence-plans/{plan_id}/skipped-occurrences",
        json={
            "occurrence_date": skip_date_morning.isoformat(),
            "reason": "Skip with morning time"
        },
        headers=headers
    )

    future_time = skip_date_afternoon + timedelta(hours=2)

    response = client.post(
        f"/recurrence-plans/{plan_id}/generate-tasks?current_time={future_time.isoformat()}",
        headers=headers
    )

    assert response.status_code == 200

    tasks = response.json()

    skipped_task_found = any(
        task.get("due_date") and 
        datetime.fromisoformat(task["due_date"].replace("Z", "+00:00")).date() == skip_date_afternoon.date()
        for task in tasks
    )

    assert not skipped_task_found, "Skipped occurrence should match regardless of time component"


def test_skip_occurrence_stored_at_start_of_day(client):
    headers = register_and_login(client, "user1@example.com")

    create_plan_response = client.post(
        "/recurrence-plans",
        json={"frequency": "daily", "interval": 1},
        headers=headers
    )

    plan_id = create_plan_response.json()["id"]

    skip_date_with_time = datetime.now().replace(hour=15, minute=30, second=45, microsecond=123456) + timedelta(days=1)

    response = client.post(
        f"/recurrence-plans/{plan_id}/skipped-occurrences",
        json={
            "occurrence_date": skip_date_with_time.isoformat(),
            "reason": "Test"
        },
        headers=headers
    )

    assert response.status_code == 201
    data = response.json()

    stored_date = datetime.fromisoformat(data["occurrence_date"].replace("Z", "+00:00"))

    assert stored_date.hour == 0
    assert stored_date.minute == 0
    assert stored_date.second == 0
    assert stored_date.microsecond == 0


# =====================
# FREQUENCY SWITCH TESTS
# =====================

def test_switch_daily_to_weekly_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "weekly",
            "week_days": [0, 2, 4]
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "weekly"
    assert data["week_days"] == [0, 2, 4]
    assert data["month_days"] is None


def test_switch_daily_to_weekly_missing_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "weekly"
        },
        headers=headers
    )

    assert switch_response.status_code == 422
    assert "week_days is required for weekly frequency" in switch_response.json()["detail"]


def test_switch_daily_to_weekly_with_month_days(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "weekly",
            "week_days": [0],
            "month_days": [1]
        },
        headers=headers
    )

    assert switch_response.status_code == 422
    assert "month_days is not allowed for weekly frequency" in switch_response.json()["detail"][0]["msg"]


def test_switch_daily_to_monthly_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "monthly",
            "month_days": [1, 15]
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "monthly"
    assert data["month_days"] == [1, 15]
    assert data["week_days"] is None


def test_switch_daily_to_monthly_missing_month_days(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "monthly"
        },
        headers=headers
    )

    assert switch_response.status_code == 422
    assert "month_days is required for monthly frequency" in switch_response.json()["detail"]


def test_switch_daily_to_monthly_with_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "monthly",
            "week_days": [0],
            "month_days": [1]
        },
        headers=headers
    )

    assert switch_response.status_code == 422
    assert "week_days is not allowed for monthly frequency" in switch_response.json()["detail"][0]["msg"]


def test_switch_daily_to_yearly_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "yearly"
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "yearly"
    assert data["week_days"] is None
    assert data["month_days"] is None


def test_switch_daily_to_yearly_with_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "daily",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "yearly",
            "week_days": [0]
        },
        headers=headers
    )

    assert switch_response.status_code == 422
    assert "week_days is not allowed for yearly frequency" in switch_response.json()["detail"][0]["msg"]


def test_switch_weekly_to_daily_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "weekly",
            "interval": 1,
            "week_days": [0, 2, 4],
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "daily"
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "daily"
    assert data["week_days"] is None
    assert data["month_days"] is None


def test_switch_weekly_to_monthly_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "weekly",
            "interval": 1,
            "week_days": [0, 2, 4],
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "monthly",
            "month_days": [1, 15]
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "monthly"
    assert data["week_days"] is None
    assert data["month_days"] == [1, 15]


def test_switch_weekly_to_monthly_with_week_days(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "weekly",
            "interval": 1,
            "week_days": [0, 2, 4],
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "monthly",
            "week_days": [1],
            "month_days": [1]
        },
        headers=headers
    )

    assert switch_response.status_code == 422
    assert "week_days is not allowed for monthly frequency" in switch_response.json()["detail"][0]["msg"]


def test_switch_monthly_to_weekly_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "monthly",
            "interval": 1,
            "month_days": [1, 15],
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "weekly",
            "week_days": [0, 2, 4]
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "weekly"
    assert data["week_days"] == [0, 2, 4]
    assert data["month_days"] is None


def test_switch_monthly_to_daily_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "monthly",
            "interval": 1,
            "month_days": [1, 15],
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "daily"
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "daily"
    assert data["week_days"] is None
    assert data["month_days"] is None


def test_switch_yearly_to_weekly_success(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "yearly",
            "interval": 1,
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    switch_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "frequency": "weekly",
            "week_days": [0, 2, 4]
        },
        headers=headers
    )

    assert switch_response.status_code == 200
    data = switch_response.json()
    assert data["frequency"] == "weekly"
    assert data["week_days"] == [0, 2, 4]
    assert data["month_days"] is None


def test_update_weekly_without_changing_frequency(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "weekly",
            "interval": 1,
            "week_days": [0, 2, 4],
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    update_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "interval": 2,
            "week_days": [1, 3, 5]
        },
        headers=headers
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["frequency"] == "weekly"
    assert data["interval"] == 2
    assert data["week_days"] == [1, 3, 5]


def test_update_monthly_without_changing_frequency(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/recurrence-plans",
        json={
            "frequency": "monthly",
            "interval": 1,
            "month_days": [1, 15],
            "is_active": True
        },
        headers=headers
    )
    plan_id = create_response.json()["id"]

    update_response = client.patch(
        f"/recurrence-plans/{plan_id}",
        json={
            "interval": 2,
            "month_days": [1, 10, 20]
        },
        headers=headers
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["frequency"] == "monthly"
    assert data["interval"] == 2
    assert data["month_days"] == [1, 10, 20]
