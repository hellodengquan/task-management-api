def register_and_login(client, email, password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================
# TAG CRUD TESTS
# =====================

def test_create_tag_requires_auth(client):
    response = client.post(
        "/tags",
        json={"name": "Bug", "color": "#ef4444"}
    )

    assert response.status_code == 401


def test_create_tag_success(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tags",
        json={"name": "Bug", "color": "#ef4444"},
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Bug"
    assert data["color"] == "#EF4444"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_tag_with_default_color(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tags",
        json={"name": "Feature"},
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Feature"
    assert data["color"] == "#3B82F6"


def test_create_duplicate_tag_name(client):
    headers = register_and_login(client, "user1@example.com")

    client.post("/tags", json={"name": "Bug"}, headers=headers)

    response = client.post(
        "/tags",
        json={"name": "Bug", "color": "#ff0000"},
        headers=headers
    )

    assert response.status_code == 400


def test_create_tag_with_invalid_color(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tags",
        json={"name": "Test", "color": "invalid"},
        headers=headers
    )

    assert response.status_code == 422


def test_list_tags_returns_own_tags(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    client.post("/tags", json={"name": "Bug"}, headers=headers1)
    client.post("/tags", json={"name": "Feature"}, headers=headers2)

    response = client.get("/tags", headers=headers1)

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Bug"


def test_get_tag_by_id(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tags",
        json={"name": "Bug", "color": "#ef4444"},
        headers=headers
    )

    tag_id = create_response.json()["id"]

    response = client.get(f"/tags/{tag_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Bug"


def test_cannot_get_another_users_tag(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post("/tags", json={"name": "Bug"}, headers=headers1)
    tag_id = create_response.json()["id"]

    response = client.get(f"/tags/{tag_id}", headers=headers2)

    assert response.status_code == 404


def test_update_tag_name(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tags",
        json={"name": "Bug", "color": "#ef4444"},
        headers=headers
    )

    tag_id = create_response.json()["id"]

    response = client.patch(
        f"/tags/{tag_id}",
        json={"name": "Issue"},
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Issue"
    assert response.json()["color"] == "#EF4444"


def test_update_tag_color(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post(
        "/tags",
        json={"name": "Bug", "color": "#ef4444"},
        headers=headers
    )

    tag_id = create_response.json()["id"]

    response = client.patch(
        f"/tags/{tag_id}",
        json={"color": "#f97316"},
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Bug"
    assert response.json()["color"] == "#F97316"


def test_cannot_update_another_users_tag(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post("/tags", json={"name": "Bug"}, headers=headers1)
    tag_id = create_response.json()["id"]

    response = client.patch(
        f"/tags/{tag_id}",
        json={"name": "Hacked"},
        headers=headers2
    )

    assert response.status_code == 404


def test_delete_tag(client):
    headers = register_and_login(client, "user1@example.com")

    create_response = client.post("/tags", json={"name": "Bug"}, headers=headers)
    tag_id = create_response.json()["id"]

    delete_response = client.delete(f"/tags/{tag_id}", headers=headers)

    assert delete_response.status_code in [200, 204]

    get_response = client.get(f"/tags/{tag_id}", headers=headers)

    assert get_response.status_code == 404


def test_cannot_delete_another_users_tag(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    create_response = client.post("/tags", json={"name": "Bug"}, headers=headers1)
    tag_id = create_response.json()["id"]

    response = client.delete(f"/tags/{tag_id}", headers=headers2)

    assert response.status_code == 404


# =====================
# TASK TAG ASSOCIATION TESTS
# =====================

def test_create_task_with_tags(client):
    headers = register_and_login(client, "user1@example.com")

    tag1 = client.post("/tags", json={"name": "Bug", "color": "#ef4444"}, headers=headers).json()
    tag2 = client.post("/tags", json={"name": "Urgent", "color": "#f97316"}, headers=headers).json()

    response = client.post(
        "/tasks",
        json={
            "title": "Fix login issue",
            "description": "Users cannot login",
            "tag_ids": [tag1["id"], tag2["id"]]
        },
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert len(data["tags"]) == 2
    tag_names = {t["name"] for t in data["tags"]}
    assert "Bug" in tag_names
    assert "Urgent" in tag_names


def test_get_task_includes_tags(client):
    headers = register_and_login(client, "user1@example.com")

    tag = client.post("/tags", json={"name": "Feature"}, headers=headers).json()

    task_response = client.post(
        "/tasks",
        json={"title": "New feature", "tag_ids": [tag["id"]]},
        headers=headers
    )

    task_id = task_response.json()["id"]

    response = client.get(f"/tasks/{task_id}", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["tags"]) == 1
    assert response.json()["tags"][0]["name"] == "Feature"


def test_list_tasks_includes_tags(client):
    headers = register_and_login(client, "user1@example.com")

    tag = client.post("/tags", json={"name": "Bug"}, headers=headers).json()

    client.post(
        "/tasks",
        json={"title": "Task with tag", "tag_ids": [tag["id"]]},
        headers=headers
    )

    client.post(
        "/tasks",
        json={"title": "Task without tag"},
        headers=headers
    )

    response = client.get("/tasks", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_update_task_tags(client):
    headers = register_and_login(client, "user1@example.com")

    tag1 = client.post("/tags", json={"name": "Bug"}, headers=headers).json()
    tag2 = client.post("/tags", json={"name": "Feature"}, headers=headers).json()

    task_response = client.post(
        "/tasks",
        json={"title": "Test task", "tag_ids": [tag1["id"]]},
        headers=headers
    )

    task_id = task_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"tag_ids": [tag2["id"]]},
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "Feature"


def test_remove_task_tags(client):
    headers = register_and_login(client, "user1@example.com")

    tag = client.post("/tags", json={"name": "Bug"}, headers=headers).json()

    task_response = client.post(
        "/tasks",
        json={"title": "Test task", "tag_ids": [tag["id"]]},
        headers=headers
    )

    task_id = task_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"tag_ids": []},
        headers=headers
    )

    assert response.status_code == 200
    assert len(response.json()["tags"]) == 0


# =====================
# FILTER TASKS BY TAGS TESTS
# =====================

def test_filter_tasks_by_single_tag(client):
    headers = register_and_login(client, "user1@example.com")

    bug_tag = client.post("/tags", json={"name": "Bug"}, headers=headers).json()
    feature_tag = client.post("/tags", json={"name": "Feature"}, headers=headers).json()

    client.post("/tasks", json={"title": "Bug 1", "tag_ids": [bug_tag["id"]]}, headers=headers)
    client.post("/tasks", json={"title": "Bug 2", "tag_ids": [bug_tag["id"]]}, headers=headers)
    client.post("/tasks", json={"title": "Feature 1", "tag_ids": [feature_tag["id"]]}, headers=headers)

    response = client.get(f"/tasks?tag_ids={bug_tag['id']}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = {t["title"] for t in data}
    assert "Bug 1" in titles
    assert "Bug 2" in titles


def test_filter_tasks_by_multiple_tags(client):
    headers = register_and_login(client, "user1@example.com")

    bug_tag = client.post("/tags", json={"name": "Bug"}, headers=headers).json()
    urgent_tag = client.post("/tags", json={"name": "Urgent"}, headers=headers).json()

    client.post("/tasks", json={"title": "Urgent Bug", "tag_ids": [bug_tag["id"], urgent_tag["id"]]}, headers=headers)
    client.post("/tasks", json={"title": "Non-urgent Bug", "tag_ids": [bug_tag["id"]]}, headers=headers)

    response = client.get(f"/tasks?tag_ids={bug_tag['id']}&tag_ids={urgent_tag['id']}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Urgent Bug"


def test_filter_with_nonexistent_tag_returns_empty(client):
    headers = register_and_login(client, "user1@example.com")

    client.post("/tasks", json={"title": "Test task"}, headers=headers)

    response = client.get("/tasks?tag_ids=999999", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 0


def test_cannot_filter_by_another_users_tag(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")

    user1_tag = client.post("/tags", json={"name": "User1 Tag"}, headers=headers1).json()

    client.post(
        "/tasks",
        json={"title": "User1 Task", "tag_ids": [user1_tag["id"]]},
        headers=headers1
    )

    response = client.get(f"/tasks?tag_ids={user1_tag['id']}", headers=headers2)

    assert response.status_code == 200
    assert len(response.json()) == 0
