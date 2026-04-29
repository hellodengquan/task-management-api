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
# NEW FIELD TESTS
# =====================

def test_create_task_with_status_and_priority(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks",
        json={
            "title": "Test task",
            "description": "Test description",
            "status": "in_progress",
            "priority": "high"
        },
        headers=headers
    )

    assert response.status_code in [200, 201]

    data = response.json()
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"
    assert data["assignee_id"] is None


def test_create_task_with_assignee(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    me_response = client.get("/tasks", headers=headers2)
    assert me_response.status_code == 200

    response = client.post(
        "/tasks",
        json={
            "title": "Assigned task",
            "assignee_id": 2
        },
        headers=headers1
    )

    assert response.status_code in [200, 201]

    data = response.json()
    assert data["assignee_id"] == 2


def test_create_task_with_invalid_assignee(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks",
        json={
            "title": "Assigned task",
            "assignee_id": 999
        },
        headers=headers
    )

    assert response.status_code == 400
    assert "Assignee not found" in response.json()["detail"]


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
        json={"status": "completed"},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["completed"] is True


def test_update_task_status_from_completed_to_pending(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task", "status": "completed"},
        headers=headers
    )

    task_id = create_response.json()["id"]
    assert create_response.json()["completed"] is True

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "pending"},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
    assert data["completed"] is False


def test_update_task_status_from_completed_to_in_progress(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task", "status": "completed"},
        headers=headers
    )

    task_id = create_response.json()["id"]
    assert create_response.json()["completed"] is True

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "in_progress"
    assert data["completed"] is False


def test_update_task_priority(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"priority": "low"},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["priority"] == "low"


def test_update_task_assignee(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task"},
        headers=headers1
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"assignee_id": 2},
        headers=headers1
    )

    assert response.status_code == 200

    data = response.json()
    assert data["assignee_id"] == 2


def test_update_task_with_invalid_assignee(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test task"},
        headers=headers
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"assignee_id": 999},
        headers=headers
    )

    assert response.status_code == 400
    assert "Assignee not found" in response.json()["detail"]


# =====================
# BATCH OPERATIONS TESTS
# =====================

def test_batch_update_requires_auth(client):
    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": [1, 2],
            "updates": {"status": "completed"}
        }
    )

    assert response.status_code == 401


def test_batch_update_success(client):
    headers = register_and_login(client, "user1@example.com")

    task1 = client.post("/tasks", json={"title": "Task 1"}, headers=headers)
    task2 = client.post("/tasks", json={"title": "Task 2"}, headers=headers)
    task3 = client.post("/tasks", json={"title": "Task 3"}, headers=headers)

    task_ids = [
        task1.json()["id"],
        task2.json()["id"],
        task3.json()["id"]
    ]

    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": task_ids,
            "updates": {"status": "completed", "priority": "high"}
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert data["success_count"] == 3
    assert data["failure_count"] == 0
    assert len(data["successes"]) == 3
    assert len(data["failures"]) == 0

    for task in data["successes"]:
        assert task["status"] == "completed"
        assert task["priority"] == "high"
        assert task["completed"] is True


def test_batch_update_with_partial_failure(client):
    headers = register_and_login(client, "user1@example.com")

    task1 = client.post("/tasks", json={"title": "Task 1"}, headers=headers)
    task2 = client.post("/tasks", json={"title": "Task 2"}, headers=headers)

    existing_ids = [task1.json()["id"], task2.json()["id"]]
    invalid_ids = [999999, 888888]
    all_ids = existing_ids + invalid_ids

    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": all_ids,
            "updates": {"status": "in_progress"}
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 4
    assert data["success_count"] == 2
    assert data["failure_count"] == 2
    assert len(data["successes"]) == 2
    assert len(data["failures"]) == 2

    for failure in data["failures"]:
        assert failure["success"] is False
        assert failure["task_id"] in invalid_ids
        assert "Task not found" in failure["detail"]


def test_batch_update_with_invalid_assignee(client):
    headers = register_and_login(client, "user1@example.com")

    task1 = client.post("/tasks", json={"title": "Task 1"}, headers=headers)
    task2 = client.post("/tasks", json={"title": "Task 2"}, headers=headers)

    task_ids = [task1.json()["id"], task2.json()["id"]]

    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": task_ids,
            "updates": {"assignee_id": 999999}
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["success_count"] == 0
    assert data["failure_count"] == 2

    for failure in data["failures"]:
        assert failure["success"] is False
        assert "Assignee not found" in failure["detail"]


def test_batch_update_status_from_completed_to_pending(client):
    headers = register_and_login(client, "user1@example.com")

    task1 = client.post("/tasks", json={"title": "Task 1", "status": "completed"}, headers=headers)
    task2 = client.post("/tasks", json={"title": "Task 2", "status": "completed"}, headers=headers)

    assert task1.json()["completed"] is True
    assert task2.json()["completed"] is True

    task_ids = [task1.json()["id"], task2.json()["id"]]

    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": task_ids,
            "updates": {"status": "pending"}
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["success_count"] == 2
    assert data["failure_count"] == 0

    for task in data["successes"]:
        assert task["status"] == "pending"
        assert task["completed"] is False


def test_batch_update_status_from_completed_to_in_progress(client):
    headers = register_and_login(client, "user1@example.com")

    task1 = client.post("/tasks", json={"title": "Task 1", "status": "completed"}, headers=headers)
    task2 = client.post("/tasks", json={"title": "Task 2", "status": "completed"}, headers=headers)

    assert task1.json()["completed"] is True
    assert task2.json()["completed"] is True

    task_ids = [task1.json()["id"], task2.json()["id"]]

    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": task_ids,
            "updates": {"status": "in_progress"}
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["success_count"] == 2
    assert data["failure_count"] == 0

    for task in data["successes"]:
        assert task["status"] == "in_progress"
        assert task["completed"] is False


def test_batch_update_with_empty_task_ids(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": [],
            "updates": {"status": "completed"}
        },
        headers=headers
    )

    assert response.status_code == 400


def test_batch_delete_requires_auth(client):
    response = client.post(
        "/tasks/batch/delete",
        json={"task_ids": [1, 2]}
    )

    assert response.status_code == 401


def test_batch_delete_success(client):
    headers = register_and_login(client, "user1@example.com")

    task1 = client.post("/tasks", json={"title": "Task 1"}, headers=headers)
    task2 = client.post("/tasks", json={"title": "Task 2"}, headers=headers)
    task3 = client.post("/tasks", json={"title": "Task 3"}, headers=headers)

    task_ids = [
        task1.json()["id"],
        task2.json()["id"],
        task3.json()["id"]
    ]

    response = client.post(
        "/tasks/batch/delete",
        json={"task_ids": task_ids},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert data["success_count"] == 3
    assert data["failure_count"] == 0
    assert len(data["successes"]) == 3
    assert len(data["failures"]) == 0

    for task_id in task_ids:
        get_response = client.get(f"/tasks/{task_id}", headers=headers)
        assert get_response.status_code == 404


def test_batch_delete_with_partial_failure(client):
    headers = register_and_login(client, "user1@example.com")

    task1 = client.post("/tasks", json={"title": "Task 1"}, headers=headers)
    task2 = client.post("/tasks", json={"title": "Task 2"}, headers=headers)

    existing_ids = [task1.json()["id"], task2.json()["id"]]
    invalid_ids = [999999, 888888]
    all_ids = existing_ids + invalid_ids

    response = client.post(
        "/tasks/batch/delete",
        json={"task_ids": all_ids},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 4
    assert data["success_count"] == 2
    assert data["failure_count"] == 2
    assert len(data["successes"]) == 2
    assert len(data["failures"]) == 2

    for failure in data["failures"]:
        assert failure["success"] is False
        assert failure["task_id"] in invalid_ids
        assert "Task not found" in failure["detail"]

    for task_id in existing_ids:
        get_response = client.get(f"/tasks/{task_id}", headers=headers)
        assert get_response.status_code == 404


def test_batch_delete_with_empty_task_ids(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks/batch/delete",
        json={"task_ids": []},
        headers=headers
    )

    assert response.status_code == 400


def test_cannot_batch_update_another_users_tasks(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Private task"},
        headers=headers1
    )

    task_id = create_response.json()["id"]

    response = client.post(
        "/tasks/batch/update",
        json={
            "task_ids": [task_id],
            "updates": {"title": "Hacked"}
        },
        headers=headers2
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["success_count"] == 0
    assert data["failure_count"] == 1
    assert data["failures"][0]["detail"] == "Task not found"


def test_cannot_batch_delete_another_users_tasks(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Private task"},
        headers=headers1
    )

    task_id = create_response.json()["id"]

    response = client.post(
        "/tasks/batch/delete",
        json={"task_ids": [task_id]},
        headers=headers2
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["success_count"] == 0
    assert data["failure_count"] == 1
    assert data["failures"][0]["detail"] == "Task not found"

    verify_response = client.get(f"/tasks/{task_id}", headers=headers1)
    assert verify_response.status_code == 200
