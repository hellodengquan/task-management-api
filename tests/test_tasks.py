def register_and_login(client, email, password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_task_requires_auth(client):
    response = client.post(
        "/tasks",
        json={"title": "Test task", "description": "Test description"}
    )

    assert response.status_code == 401


def test_create_task_success(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks",
        json={"title": "Test task", "description": "Test description"},
        headers=headers
    )

    assert response.status_code in [200, 201]

    data = response.json()
    assert data["title"] == "Test task"
    assert data["description"] == "Test description"
    assert data["completed"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_task_invalid_payload(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks",
        json={"title": "", "description": "Test description"},
        headers=headers
    )

    assert response.status_code == 422


def test_list_tasks_only_returns_own_tasks(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    client.post("/tasks", json={"title": "User 1 task"}, headers=headers1)
    client.post("/tasks", json={"title": "User 2 task"}, headers=headers2)

    response = client.get("/tasks", headers=headers1)

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "User 1 task"


def test_get_own_task(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "My task", "description": "Mine"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == "My task"


def test_cannot_get_another_users_task(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Private task"},
        headers=headers1
    )

    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}", headers=headers2)

    assert response.status_code in [403, 404]


def test_update_own_task(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Old title"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"title": "New title", "completed": True},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "New title"
    assert data["completed"] is True


def test_cannot_update_another_users_task(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Private task"},
        headers=headers1
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"title": "Hacked"},
        headers=headers2
    )

    assert response.status_code in [403, 404]


def test_delete_own_task(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Delete me"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    delete_response = client.delete(f"/tasks/{task_id}", headers=headers)

    assert delete_response.status_code in [200, 204]

    get_response = client.get(f"/tasks/{task_id}", headers=headers)

    assert get_response.status_code == 404


def test_cannot_delete_another_users_task(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Private task"},
        headers=headers1
    )

    task_id = create_response.json()["id"]

    response = client.delete(f"/tasks/{task_id}", headers=headers2)

    assert response.status_code in [403, 404]


def test_task_default_status_is_pending(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks",
        json={"title": "Test task"},
        headers=headers
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["status"] == "pending"
    assert data["completed"] is False


def test_create_task_with_specific_status(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks",
        json={"title": "In progress task", "status": "in_progress"},
        headers=headers
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["completed"] is False

    response2 = client.post(
        "/tasks",
        json={"title": "Completed task", "status": "completed"},
        headers=headers
    )

    assert response2.status_code in [200, 201]
    data2 = response2.json()
    assert data2["status"] == "completed"
    assert data2["completed"] is True


def test_update_task_status(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task"},
        headers=headers
    )
    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["completed"] is False

    response2 = client.patch(
        f"/tasks/{task_id}",
        json={"status": "completed"},
        headers=headers
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "completed"
    assert data2["completed"] is True


def test_update_completed_syncs_status(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task", "status": "in_progress"},
        headers=headers
    )
    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"completed": True},
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed"] is True


def test_update_status_syncs_completed(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task", "status": "completed"},
        headers=headers
    )
    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["completed"] is False


def test_filter_tasks_by_status(client):
    headers = register_and_login(client, "user1@example.com")

    client.post("/tasks", json={"title": "Pending task", "status": "pending"}, headers=headers)
    client.post("/tasks", json={"title": "In progress task", "status": "in_progress"}, headers=headers)
    client.post("/tasks", json={"title": "Completed task", "status": "completed"}, headers=headers)

    pending_response = client.get("/tasks?status=pending", headers=headers)
    assert pending_response.status_code == 200
    pending_tasks = pending_response.json()
    assert len(pending_tasks) == 1
    assert pending_tasks[0]["status"] == "pending"

    in_progress_response = client.get("/tasks?status=in_progress", headers=headers)
    assert in_progress_response.status_code == 200
    in_progress_tasks = in_progress_response.json()
    assert len(in_progress_tasks) == 1
    assert in_progress_tasks[0]["status"] == "in_progress"

    completed_response = client.get("/tasks?status=completed", headers=headers)
    assert completed_response.status_code == 200
    completed_tasks = completed_response.json()
    assert len(completed_tasks) == 1
    assert completed_tasks[0]["status"] == "completed"


def test_exclude_completed_tasks(client):
    headers = register_and_login(client, "user1@example.com")

    client.post("/tasks", json={"title": "Pending task", "status": "pending"}, headers=headers)
    client.post("/tasks", json={"title": "In progress task", "status": "in_progress"}, headers=headers)
    client.post("/tasks", json={"title": "Completed task", "status": "completed"}, headers=headers)

    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    all_tasks = response.json()
    assert len(all_tasks) == 3

    response2 = client.get("/tasks?exclude_completed=true", headers=headers)
    assert response2.status_code == 200
    incomplete_tasks = response2.json()
    assert len(incomplete_tasks) == 2

    statuses = [task["status"] for task in incomplete_tasks]
    assert "pending" in statuses
    assert "in_progress" in statuses
    assert "completed" not in statuses
