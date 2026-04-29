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
