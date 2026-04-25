import pytest


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


def test_create_subtask_with_valid_parent(client):
    headers = register_and_login(client, "user@example.com")

    parent_response = client.post(
        "/tasks",
        json={"title": "Parent Task"},
        headers=headers
    )
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/tasks",
        json={"title": "Child Task", "parent_id": parent_id},
        headers=headers
    )
    assert child_response.status_code == 201
    child_data = child_response.json()
    assert child_data["parent_id"] == parent_id
    assert child_data["progress"] == 0.0


def test_create_subtask_with_invalid_parent(client):
    headers = register_and_login(client, "user@example.com")

    response = client.post(
        "/tasks",
        json={"title": "Child Task", "parent_id": 99999},
        headers=headers
    )
    assert response.status_code == 400


def test_cannot_create_subtask_with_another_users_parent(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    parent_response = client.post(
        "/tasks",
        json={"title": "User1's Task"},
        headers=headers1
    )
    parent_id = parent_response.json()["id"]

    response = client.post(
        "/tasks",
        json={"title": "User2's Task", "parent_id": parent_id},
        headers=headers2
    )
    assert response.status_code == 400


def test_get_subtasks(client):
    headers = register_and_login(client, "user@example.com")

    parent_response = client.post(
        "/tasks",
        json={"title": "Parent Task"},
        headers=headers
    )
    parent_id = parent_response.json()["id"]

    client.post(
        "/tasks",
        json={"title": "Child 1", "parent_id": parent_id},
        headers=headers
    )
    client.post(
        "/tasks",
        json={"title": "Child 2", "parent_id": parent_id},
        headers=headers
    )

    subtasks_response = client.get(
        f"/tasks/{parent_id}/subtasks",
        headers=headers
    )
    assert subtasks_response.status_code == 200
    subtasks = subtasks_response.json()
    assert len(subtasks) == 2
    titles = [t["title"] for t in subtasks]
    assert "Child 1" in titles
    assert "Child 2" in titles


def test_progress_calculation_with_subtasks(client):
    headers = register_and_login(client, "user@example.com")

    parent_response = client.post(
        "/tasks",
        json={"title": "Parent Task"},
        headers=headers
    )
    parent_id = parent_response.json()["id"]

    child1_response = client.post(
        "/tasks",
        json={"title": "Child 1", "parent_id": parent_id},
        headers=headers
    )
    child1_id = child1_response.json()["id"]

    child2_response = client.post(
        "/tasks",
        json={"title": "Child 2", "parent_id": parent_id},
        headers=headers
    )
    child2_id = child2_response.json()["id"]

    parent_response = client.get(f"/tasks/{parent_id}", headers=headers)
    assert parent_response.json()["progress"] == 0.0

    client.patch(
        f"/tasks/{child1_id}",
        json={"completed": True},
        headers=headers
    )

    parent_response = client.get(f"/tasks/{parent_id}", headers=headers)
    assert parent_response.json()["progress"] == pytest.approx(33.33, rel=1e-2)

    client.patch(
        f"/tasks/{child2_id}",
        json={"completed": True},
        headers=headers
    )
    client.patch(
        f"/tasks/{parent_id}",
        json={"completed": True},
        headers=headers
    )

    parent_response = client.get(f"/tasks/{parent_id}", headers=headers)
    assert parent_response.json()["progress"] == 100.0


def test_progress_calculation_nested_subtasks(client):
    headers = register_and_login(client, "user@example.com")

    grandparent_response = client.post(
        "/tasks",
        json={"title": "Grandparent"},
        headers=headers
    )
    grandparent_id = grandparent_response.json()["id"]

    parent_response = client.post(
        "/tasks",
        json={"title": "Parent", "parent_id": grandparent_id},
        headers=headers
    )
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/tasks",
        json={"title": "Child", "parent_id": parent_id},
        headers=headers
    )
    child_id = child_response.json()["id"]

    grandparent_response = client.get(f"/tasks/{grandparent_id}", headers=headers)
    assert grandparent_response.json()["progress"] == 0.0

    client.patch(
        f"/tasks/{child_id}",
        json={"completed": True},
        headers=headers
    )

    grandparent_response = client.get(f"/tasks/{grandparent_id}", headers=headers)
    assert grandparent_response.json()["progress"] == pytest.approx(33.33, rel=1e-2)

    parent_response = client.get(f"/tasks/{parent_id}", headers=headers)
    assert parent_response.json()["progress"] == 50.0


def test_update_task_parent_id(client):
    headers = register_and_login(client, "user@example.com")

    parent1_response = client.post(
        "/tasks",
        json={"title": "Parent 1"},
        headers=headers
    )
    parent1_id = parent1_response.json()["id"]

    parent2_response = client.post(
        "/tasks",
        json={"title": "Parent 2"},
        headers=headers
    )
    parent2_id = parent2_response.json()["id"]

    child_response = client.post(
        "/tasks",
        json={"title": "Child", "parent_id": parent1_id},
        headers=headers
    )
    child_id = child_response.json()["id"]
    assert child_response.json()["parent_id"] == parent1_id

    update_response = client.patch(
        f"/tasks/{child_id}",
        json={"parent_id": parent2_id},
        headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["parent_id"] == parent2_id


def test_cannot_set_parent_to_self(client):
    headers = register_and_login(client, "user@example.com")

    task_response = client.post(
        "/tasks",
        json={"title": "Task"},
        headers=headers
    )
    task_id = task_response.json()["id"]

    update_response = client.patch(
        f"/tasks/{task_id}",
        json={"parent_id": task_id},
        headers=headers
    )
    assert update_response.status_code == 404


def test_cannot_create_circular_reference(client):
    headers = register_and_login(client, "user@example.com")

    parent_response = client.post(
        "/tasks",
        json={"title": "Parent"},
        headers=headers
    )
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/tasks",
        json={"title": "Child", "parent_id": parent_id},
        headers=headers
    )
    child_id = child_response.json()["id"]

    update_response = client.patch(
        f"/tasks/{parent_id}",
        json={"parent_id": child_id},
        headers=headers
    )
    assert update_response.status_code == 404


def test_cascade_delete_subtasks(client):
    headers = register_and_login(client, "user@example.com")

    parent_response = client.post(
        "/tasks",
        json={"title": "Parent"},
        headers=headers
    )
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/tasks",
        json={"title": "Child", "parent_id": parent_id},
        headers=headers
    )
    child_id = child_response.json()["id"]

    child_check = client.get(f"/tasks/{child_id}", headers=headers)
    assert child_check.status_code == 200

    client.delete(f"/tasks/{parent_id}", headers=headers)

    parent_check = client.get(f"/tasks/{parent_id}", headers=headers)
    assert parent_check.status_code == 404

    child_check = client.get(f"/tasks/{child_id}", headers=headers)
    assert child_check.status_code == 404


def test_list_tasks_with_parent_id_filter(client):
    headers = register_and_login(client, "user@example.com")

    client.post(
        "/tasks",
        json={"title": "Root Task 1"},
        headers=headers
    )
    root2_response = client.post(
        "/tasks",
        json={"title": "Root Task 2"},
        headers=headers
    )
    root2_id = root2_response.json()["id"]

    client.post(
        "/tasks",
        json={"title": "Subtask of Root 2", "parent_id": root2_id},
        headers=headers
    )

    root_tasks = client.get("/tasks", headers=headers)
    assert len(root_tasks.json()) == 2

    subtasks = client.get(f"/tasks?parent_id={root2_id}", headers=headers)
    assert len(subtasks.json()) == 1
    assert subtasks.json()[0]["title"] == "Subtask of Root 2"


def test_task_out_includes_progress(client):
    headers = register_and_login(client, "user@example.com")

    create_response = client.post(
        "/tasks",
        json={"title": "Test Task"},
        headers=headers
    )
    task_id = create_response.json()["id"]

    assert "progress" in create_response.json()
    assert create_response.json()["progress"] == 0.0

    get_response = client.get(f"/tasks/{task_id}", headers=headers)
    assert "progress" in get_response.json()

    list_response = client.get("/tasks", headers=headers)
    assert "progress" in list_response.json()[0]

    update_response = client.patch(
        f"/tasks/{task_id}",
        json={"completed": True},
        headers=headers
    )
    assert update_response.json()["progress"] == 100.0
