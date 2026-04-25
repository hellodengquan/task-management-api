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


# =====================
# TASK HISTORY TESTS
# =====================

def test_create_task_records_history(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task", "description": "Test description"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    history_response = client.get(f"/tasks/{task_id}/history", headers=headers)

    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 1

    record = history[0]
    assert record["task_id"] == task_id
    assert record["action"] == "create"
    assert record["details"]["title"] == "Test task"
    assert record["details"]["description"] == "Test description"
    assert "created_at" in record


def test_update_task_records_history(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Old title", "description": "Old description"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    client.patch(
        f"/tasks/{task_id}",
        json={"title": "New title", "completed": True},
        headers=headers
    )

    history_response = client.get(f"/tasks/{task_id}/history", headers=headers)

    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 2

    create_record = history[0]
    assert create_record["action"] == "create"

    update_record = history[1]
    assert update_record["action"] == "update"
    assert update_record["details"]["title"]["old"] == "Old title"
    assert update_record["details"]["title"]["new"] == "New title"
    assert update_record["details"]["completed"]["old"] == False
    assert update_record["details"]["completed"]["new"] == True
    assert "description" not in update_record["details"]


def test_update_without_changes_does_not_record_history(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    client.patch(
        f"/tasks/{task_id}",
        json={"title": "Test task", "completed": False},
        headers=headers
    )

    history_response = client.get(f"/tasks/{task_id}/history", headers=headers)

    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 1
    assert history[0]["action"] == "create"


def test_delete_task_records_history(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Delete me", "description": "Will be deleted", "completed": False},
        headers=headers
    )

    task_id = create_response.json()["id"]

    client.delete(f"/tasks/{task_id}", headers=headers)

    history_response = client.get(f"/tasks/{task_id}/history", headers=headers)

    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 2

    create_record = history[0]
    assert create_record["action"] == "create"

    delete_record = history[1]
    assert delete_record["action"] == "delete"
    assert delete_record["details"]["title"] == "Delete me"
    assert delete_record["details"]["description"] == "Will be deleted"
    assert delete_record["details"]["completed"] == False


def test_get_history_requires_auth(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}/history")

    assert response.status_code == 401


def test_cannot_get_another_users_history(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Private task"},
        headers=headers1
    )

    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}/history", headers=headers2)

    assert response.status_code in [403, 404]


def test_get_history_for_nonexistent_task(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.get("/tasks/999999/history", headers=headers)

    assert response.status_code == 404
