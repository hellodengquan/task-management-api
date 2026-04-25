def register_and_login(client, email, password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_test_task(client, headers, title="Test task"):
    response = client.post(
        "/tasks",
        json={"title": title},
        headers=headers
    )
    return response.json()["id"]


def test_create_comment_requires_auth(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Test comment"}
    )

    assert response.status_code == 401


def test_create_comment_success(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Test comment content"},
        headers=headers
    )

    assert response.status_code == 201

    data = response.json()
    assert data["content"] == "Test comment content"
    assert data["task_id"] == task_id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_comment_invalid_payload(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": ""},
        headers=headers
    )

    assert response.status_code == 422


def test_create_comment_on_nonexistent_task(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.post(
        "/tasks/9999/comments",
        json={"content": "Test comment"},
        headers=headers
    )

    assert response.status_code == 404


def test_get_task_comments_success(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "First comment"},
        headers=headers
    )
    client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Second comment"},
        headers=headers
    )

    response = client.get(f"/tasks/{task_id}/comments", headers=headers)

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["content"] == "Second comment"
    assert data["items"][1]["content"] == "First comment"
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_get_comments_on_nonexistent_task(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.get("/tasks/9999/comments", headers=headers)

    assert response.status_code == 404


def test_delete_own_comment(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    create_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Delete me"},
        headers=headers
    )

    comment_id = create_response.json()["id"]

    delete_response = client.delete(f"/comments/{comment_id}", headers=headers)

    assert delete_response.status_code == 204

    get_response = client.get(f"/tasks/{task_id}/comments", headers=headers)

    assert get_response.json()["total"] == 0
    assert len(get_response.json()["items"]) == 0


def test_cannot_delete_another_users_comment(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")
    task_id = create_test_task(client, headers1, "Shared task")

    create_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "User 1's comment"},
        headers=headers1
    )

    comment_id = create_response.json()["id"]

    response = client.delete(f"/comments/{comment_id}", headers=headers2)

    assert response.status_code == 403


def test_delete_nonexistent_comment(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.delete("/comments/9999", headers=headers)

    assert response.status_code == 404


def test_update_own_comment(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    create_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Original content"},
        headers=headers
    )

    comment_id = create_response.json()["id"]
    original_updated_at = create_response.json()["updated_at"]

    update_response = client.patch(
        f"/comments/{comment_id}",
        json={"content": "Updated content"},
        headers=headers
    )

    assert update_response.status_code == 200

    data = update_response.json()
    assert data["content"] == "Updated content"
    assert data["id"] == comment_id
    assert data["updated_at"] != original_updated_at


def test_cannot_update_another_users_comment(client):
    headers1 = register_and_login(client, "user1@example.com")
    headers2 = register_and_login(client, "user2@example.com")
    task_id = create_test_task(client, headers1, "Shared task")

    create_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "User 1's comment"},
        headers=headers1
    )

    comment_id = create_response.json()["id"]

    response = client.patch(
        f"/comments/{comment_id}",
        json={"content": "Hacked content"},
        headers=headers2
    )

    assert response.status_code == 403


def test_update_nonexistent_comment(client):
    headers = register_and_login(client, "user1@example.com")

    response = client.patch(
        "/comments/9999",
        json={"content": "Updated content"},
        headers=headers
    )

    assert response.status_code == 404


def test_update_comment_invalid_payload(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    create_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Original content"},
        headers=headers
    )

    comment_id = create_response.json()["id"]

    response = client.patch(
        f"/comments/{comment_id}",
        json={"content": ""},
        headers=headers
    )

    assert response.status_code == 422


def test_update_comment_requires_auth(client):
    headers = register_and_login(client, "user1@example.com")
    task_id = create_test_task(client, headers)

    create_response = client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Original content"},
        headers=headers
    )

    comment_id = create_response.json()["id"]

    response = client.patch(
        f"/comments/{comment_id}",
        json={"content": "Updated content"}
    )

    assert response.status_code == 401


def test_get_comments_with_pagination(client):
    headers = register_and_login(client, "pagination1@example.com")
    task_id = create_test_task(client, headers)

    # 创建25条评论
    for i in range(25):
        client.post(
            f"/tasks/{task_id}/comments",
            json={"content": f"Comment {i}"},
            headers=headers
        )

    # 测试默认分页（前20条）
    response1 = client.get(f"/tasks/{task_id}/comments", headers=headers)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["total"] == 25
    assert len(data1["items"]) == 20
    assert data1["items"][0]["content"] == "Comment 24"
    assert data1["items"][19]["content"] == "Comment 5"
    assert data1["skip"] == 0
    assert data1["limit"] == 20

    # 测试第二页（skip=20, limit=20）
    response2 = client.get(f"/tasks/{task_id}/comments?skip=20&limit=20", headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["total"] == 25
    assert len(data2["items"]) == 5
    assert data2["items"][0]["content"] == "Comment 4"
    assert data2["items"][4]["content"] == "Comment 0"
    assert data2["skip"] == 20
    assert data2["limit"] == 20

    # 测试自定义limit
    response3 = client.get(f"/tasks/{task_id}/comments?skip=0&limit=5", headers=headers)
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3["total"] == 25
    assert len(data3["items"]) == 5
    assert data3["items"][0]["content"] == "Comment 24"
    assert data3["items"][4]["content"] == "Comment 20"
    assert data3["skip"] == 0
    assert data3["limit"] == 5


def test_get_comments_pagination_boundary(client):
    headers = register_and_login(client, "pagination2@example.com")
    task_id = create_test_task(client, headers)

    # 创建5条评论
    for i in range(5):
        client.post(
            f"/tasks/{task_id}/comments",
            json={"content": f"Comment {i}"},
            headers=headers
        )

    # 测试skip超出范围
    response = client.get(f"/tasks/{task_id}/comments?skip=10&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 0


def test_pagination_parameter_validation(client):
    headers = register_and_login(client, "validation@example.com")
    task_id = create_test_task(client, headers)

    # 创建一些评论
    for i in range(5):
        client.post(
            f"/tasks/{task_id}/comments",
            json={"content": f"Comment {i}"},
            headers=headers
        )

    # 测试skip为负数（应该返回422）
    response1 = client.get(f"/tasks/{task_id}/comments?skip=-1&limit=10", headers=headers)
    assert response1.status_code == 422

    # 测试limit为0（应该返回422）
    response2 = client.get(f"/tasks/{task_id}/comments?skip=0&limit=0", headers=headers)
    assert response2.status_code == 422

    # 测试limit为负数（应该返回422）
    response3 = client.get(f"/tasks/{task_id}/comments?skip=0&limit=-5", headers=headers)
    assert response3.status_code == 422

    # 测试limit超过100（应该返回422）
    response4 = client.get(f"/tasks/{task_id}/comments?skip=0&limit=101", headers=headers)
    assert response4.status_code == 422

    # 测试有效的参数（应该正常返回）
    response5 = client.get(f"/tasks/{task_id}/comments?skip=0&limit=100", headers=headers)
    assert response5.status_code == 200
    data = response5.json()
    assert data["total"] == 5
    assert data["limit"] == 100