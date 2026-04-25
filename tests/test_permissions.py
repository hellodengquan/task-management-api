def register_and_login(client, email, password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestTaskIsolation:
    def test_admin_can_see_all_tasks(self, client, db_session, admin_headers):
        member1_headers = register_and_login(client, "member1@example.com")
        member2_headers = register_and_login(client, "member2@example.com")

        client.post("/tasks", json={"title": "Member 1 task"}, headers=member1_headers)
        client.post("/tasks", json={"title": "Member 2 task"}, headers=member2_headers)

        response = client.get("/tasks", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {task["title"] for task in data}
        assert "Member 1 task" in titles
        assert "Member 2 task" in titles

    def test_admin_can_get_any_users_task(self, client, db_session, admin_headers):
        member_headers = register_and_login(client, "member@example.com")

        create_response = client.post(
            "/tasks", 
            json={"title": "Member task"}, 
            headers=member_headers
        )
        task_id = create_response.json()["id"]

        response = client.get(f"/tasks/{task_id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Member task"

    def test_admin_can_update_any_users_task(self, client, db_session, admin_headers):
        member_headers = register_and_login(client, "member@example.com")

        create_response = client.post(
            "/tasks", 
            json={"title": "Original title"}, 
            headers=member_headers
        )
        task_id = create_response.json()["id"]

        update_response = client.patch(
            f"/tasks/{task_id}",
            json={"title": "Updated by admin", "completed": True},
            headers=admin_headers
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Updated by admin"
        assert update_response.json()["completed"] is True

        verify_response = client.get(f"/tasks/{task_id}", headers=member_headers)
        assert verify_response.json()["title"] == "Updated by admin"
        assert verify_response.json()["completed"] is True

    def test_admin_can_delete_any_users_task(self, client, db_session, admin_headers):
        member_headers = register_and_login(client, "member@example.com")

        create_response = client.post(
            "/tasks", 
            json={"title": "Task to delete"}, 
            headers=member_headers
        )
        task_id = create_response.json()["id"]

        delete_response = client.delete(f"/tasks/{task_id}", headers=admin_headers)
        assert delete_response.status_code == 204

        get_response = client.get(f"/tasks/{task_id}", headers=member_headers)
        assert get_response.status_code == 404

    def test_member_can_only_see_own_tasks(self, client):
        member1_headers = register_and_login(client, "member1@example.com")
        member2_headers = register_and_login(client, "member2@example.com")

        client.post("/tasks", json={"title": "Member 1 task"}, headers=member1_headers)
        client.post("/tasks", json={"title": "Member 2 task"}, headers=member2_headers)

        response = client.get("/tasks", headers=member1_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Member 1 task"

    def test_member_cannot_get_another_users_task(self, client):
        member1_headers = register_and_login(client, "member1@example.com")
        member2_headers = register_and_login(client, "member2@example.com")

        create_response = client.post(
            "/tasks", 
            json={"title": "Private task"}, 
            headers=member1_headers
        )
        task_id = create_response.json()["id"]

        response = client.get(f"/tasks/{task_id}", headers=member2_headers)
        assert response.status_code == 404

    def test_member_cannot_update_another_users_task(self, client):
        member1_headers = register_and_login(client, "member1@example.com")
        member2_headers = register_and_login(client, "member2@example.com")

        create_response = client.post(
            "/tasks", 
            json={"title": "Private task"}, 
            headers=member1_headers
        )
        task_id = create_response.json()["id"]

        response = client.patch(
            f"/tasks/{task_id}",
            json={"title": "Hacked"},
            headers=member2_headers
        )
        assert response.status_code == 404

    def test_member_cannot_delete_another_users_task(self, client):
        member1_headers = register_and_login(client, "member1@example.com")
        member2_headers = register_and_login(client, "member2@example.com")

        create_response = client.post(
            "/tasks", 
            json={"title": "Private task"}, 
            headers=member1_headers
        )
        task_id = create_response.json()["id"]

        response = client.delete(f"/tasks/{task_id}", headers=member2_headers)
        assert response.status_code == 404


class TestUserListEndpoint:
    def test_admin_can_get_user_list(self, client, admin_headers):
        register_and_login(client, "user1@example.com")
        register_and_login(client, "user2@example.com")

        response = client.get("/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        emails = {user["email"] for user in data}
        assert "admin@example.com" in emails
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    def test_admin_can_get_single_user(self, client, admin_headers):
        member_headers = register_and_login(client, "member@example.com")
        register_response = client.post(
            "/auth/register", 
            json={"email": "target@example.com", "password": "password123"}
        )
        target_user_id = register_response.json()["id"]

        response = client.get(f"/users/{target_user_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "target@example.com"
        assert data["role"] == "member"
        assert "id" in data
        assert "created_at" in data

    def test_member_cannot_get_user_list(self, client, member_headers):
        response = client.get("/users", headers=member_headers)
        assert response.status_code == 403

    def test_member_cannot_get_single_user(self, client, member_headers):
        register_response = client.post(
            "/auth/register", 
            json={"email": "target@example.com", "password": "password123"}
        )
        target_user_id = register_response.json()["id"]

        response = client.get(f"/users/{target_user_id}", headers=member_headers)
        assert response.status_code == 403

    def test_unauthenticated_cannot_get_user_list(self, client):
        response = client.get("/users")
        assert response.status_code == 401

    def test_admin_get_nonexistent_user_returns_404(self, client, admin_headers):
        response = client.get("/users/99999", headers=admin_headers)
        assert response.status_code == 404


class TestRoleUpdateEndpoint:
    def test_admin_can_promote_member_to_admin(self, client, db_session, admin_headers):
        register_response = client.post(
            "/auth/register", 
            json={"email": "newadmin@example.com", "password": "password123"}
        )
        user_id = register_response.json()["id"]
        assert register_response.json()["role"] == "member"

        update_response = client.patch(
            f"/users/{user_id}/role",
            json={"role": "admin"},
            headers=admin_headers
        )
        assert update_response.status_code == 200
        assert update_response.json()["role"] == "admin"

        login_response = client.post(
            "/auth/login",
            data={"username": "newadmin@example.com", "password": "password123"}
        )
        new_admin_token = login_response.json()["access_token"]
        new_admin_headers = {"Authorization": f"Bearer {new_admin_token}"}

        user_list_response = client.get("/users", headers=new_admin_headers)
        assert user_list_response.status_code == 200

    def test_admin_can_demote_admin_to_member(self, client, db_session, admin_headers):
        register_response = client.post(
            "/auth/register", 
            json={"email": "temporaryadmin@example.com", "password": "password123"}
        )
        user_id = register_response.json()["id"]

        client.patch(
            f"/users/{user_id}/role",
            json={"role": "admin"},
            headers=admin_headers
        )

        demote_response = client.patch(
            f"/users/{user_id}/role",
            json={"role": "member"},
            headers=admin_headers
        )
        assert demote_response.status_code == 200
        assert demote_response.json()["role"] == "member"

    def test_member_cannot_update_user_role(self, client, member_headers):
        register_response = client.post(
            "/auth/register", 
            json={"email": "target@example.com", "password": "password123"}
        )
        user_id = register_response.json()["id"]

        response = client.patch(
            f"/users/{user_id}/role",
            json={"role": "admin"},
            headers=member_headers
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_update_user_role(self, client):
        response = client.patch(
            "/users/1/role",
            json={"role": "admin"}
        )
        assert response.status_code == 401

    def test_admin_update_nonexistent_user_returns_404(self, client, admin_headers):
        response = client.patch(
            "/users/99999/role",
            json={"role": "admin"},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_invalid_role_returns_422(self, client, admin_headers):
        register_response = client.post(
            "/auth/register", 
            json={"email": "testuser@example.com", "password": "password123"}
        )
        user_id = register_response.json()["id"]

        response = client.patch(
            f"/users/{user_id}/role",
            json={"role": "invalid_role"},
            headers=admin_headers
        )
        assert response.status_code == 422

    def test_user_out_response_includes_role(self, client):
        register_response = client.post(
            "/auth/register", 
            json={"email": "test@example.com", "password": "password123"}
        )
        assert register_response.status_code == 201
        data = register_response.json()
        assert "role" in data
        assert data["role"] == "member"
