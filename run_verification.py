import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os

from app.db import Base
from app.deps import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_verification.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)
client = TestClient(app)

def register_and_login(email, password="password123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def run_tests():
    results = []
    
    # Test 1: 健康检查
    print("测试1: 健康检查...", end=" ")
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        results.append(("健康检查", "通过"))
        print("通过")
    except Exception as e:
        results.append(("健康检查", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 2: 用户注册和登录
    print("测试2: 用户注册和登录...", end=" ")
    try:
        headers = register_and_login("testuser@example.com")
        assert "Authorization" in headers
        results.append(("用户注册和登录", "通过"))
        print("通过")
    except Exception as e:
        results.append(("用户注册和登录", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 3: 创建任务
    print("测试3: 创建任务...", end=" ")
    try:
        headers = register_and_login("taskuser@example.com")
        response = client.post(
            "/tasks",
            json={"title": "Test Task"},
            headers=headers
        )
        assert response.status_code == 201
        task_id = response.json()["id"]
        results.append(("创建任务", "通过"))
        print("通过")
    except Exception as e:
        results.append(("创建任务", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 4: 创建评论
    print("测试4: 创建评论...", end=" ")
    try:
        headers = register_and_login("commentuser@example.com")
        task_response = client.post(
            "/tasks",
            json={"title": "Comment Task"},
            headers=headers
        )
        task_id = task_response.json()["id"]
        
        comment_response = client.post(
            f"/tasks/{task_id}/comments",
            json={"content": "Test comment content"},
            headers=headers
        )
        assert comment_response.status_code == 201
        assert comment_response.json()["content"] == "Test comment content"
        results.append(("创建评论", "通过"))
        print("通过")
    except Exception as e:
        results.append(("创建评论", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 5: 获取评论
    print("测试5: 获取评论列表...", end=" ")
    try:
        headers = register_and_login("getcomments@example.com")
        task_response = client.post(
            "/tasks",
            json={"title": "Get Comments Task"},
            headers=headers
        )
        task_id = task_response.json()["id"]
        
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
        assert len(response.json()) == 2
        results.append(("获取评论列表", "通过"))
        print("通过")
    except Exception as e:
        results.append(("获取评论列表", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 6: 更新评论
    print("测试6: 更新评论...", end=" ")
    try:
        headers = register_and_login("updatecomment@example.com")
        task_response = client.post(
            "/tasks",
            json={"title": "Update Comment Task"},
            headers=headers
        )
        task_id = task_response.json()["id"]
        
        comment_response = client.post(
            f"/tasks/{task_id}/comments",
            json={"content": "Original content"},
            headers=headers
        )
        comment_id = comment_response.json()["id"]
        
        update_response = client.patch(
            f"/comments/{comment_id}",
            json={"content": "Updated content"},
            headers=headers
        )
        assert update_response.status_code == 200
        assert update_response.json()["content"] == "Updated content"
        results.append(("更新评论", "通过"))
        print("通过")
    except Exception as e:
        results.append(("更新评论", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 7: 评论分页
    print("测试7: 评论分页...", end=" ")
    try:
        headers = register_and_login("pagination@example.com")
        task_response = client.post(
            "/tasks",
            json={"title": "Pagination Task"},
            headers=headers
        )
        task_id = task_response.json()["id"]
        
        for i in range(25):
            client.post(
                f"/tasks/{task_id}/comments",
                json={"content": f"Comment {i}"},
                headers=headers
            )
        
        response1 = client.get(f"/tasks/{task_id}/comments", headers=headers)
        assert response1.status_code == 200
        assert len(response1.json()) == 20
        
        response2 = client.get(f"/tasks/{task_id}/comments?skip=20&limit=20", headers=headers)
        assert response2.status_code == 200
        assert len(response2.json()) == 5
        
        results.append(("评论分页", "通过"))
        print("通过")
    except Exception as e:
        results.append(("评论分页", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 8: 删除评论
    print("测试8: 删除评论...", end=" ")
    try:
        headers = register_and_login("deletecomment@example.com")
        task_response = client.post(
            "/tasks",
            json={"title": "Delete Comment Task"},
            headers=headers
        )
        task_id = task_response.json()["id"]
        
        comment_response = client.post(
            f"/tasks/{task_id}/comments",
            json={"content": "Delete me"},
            headers=headers
        )
        comment_id = comment_response.json()["id"]
        
        delete_response = client.delete(f"/comments/{comment_id}", headers=headers)
        assert delete_response.status_code == 204
        
        get_response = client.get(f"/tasks/{task_id}/comments", headers=headers)
        assert len(get_response.json()) == 0
        
        results.append(("删除评论", "通过"))
        print("通过")
    except Exception as e:
        results.append(("删除评论", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 9: 权限控制 - 不能修改他人评论
    print("测试9: 权限控制 - 不能修改他人评论...", end=" ")
    try:
        headers1 = register_and_login("user1@example.com")
        headers2 = register_and_login("user2@example.com")
        
        task_response = client.post(
            "/tasks",
            json={"title": "Shared Task"},
            headers=headers1
        )
        task_id = task_response.json()["id"]
        
        comment_response = client.post(
            f"/tasks/{task_id}/comments",
            json={"content": "User 1's comment"},
            headers=headers1
        )
        comment_id = comment_response.json()["id"]
        
        update_response = client.patch(
            f"/comments/{comment_id}",
            json={"content": "Hacked!"},
            headers=headers2
        )
        assert update_response.status_code == 403
        
        results.append(("权限控制 - 不能修改他人评论", "通过"))
        print("通过")
    except Exception as e:
        results.append(("权限控制 - 不能修改他人评论", f"失败: {e}"))
        print(f"失败: {e}")
    
    # Test 10: 权限控制 - 不能删除他人评论
    print("测试10: 权限控制 - 不能删除他人评论...", end=" ")
    try:
        headers1 = register_and_login("user3@example.com")
        headers2 = register_and_login("user4@example.com")
        
        task_response = client.post(
            "/tasks",
            json={"title": "Another Shared Task"},
            headers=headers1
        )
        task_id = task_response.json()["id"]
        
        comment_response = client.post(
            f"/tasks/{task_id}/comments",
            json={"content": "User 3's comment"},
            headers=headers1
        )
        comment_id = comment_response.json()["id"]
        
        delete_response = client.delete(f"/comments/{comment_id}", headers=headers2)
        assert delete_response.status_code == 403
        
        results.append(("权限控制 - 不能删除他人评论", "通过"))
        print("通过")
    except Exception as e:
        results.append(("权限控制 - 不能删除他人评论", f"失败: {e}"))
        print(f"失败: {e}")
    
    # 清理
    engine.dispose()
    if os.path.exists("test_verification.db"):
        os.remove("test_verification.db")
    
    # 打印测试结果汇总
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    
    passed = 0
    failed = 0
    for test_name, result in results:
        if "通过" in result:
            passed += 1
            print(f"✓ {test_name}: {result}")
        else:
            failed += 1
            print(f"✗ {test_name}: {result}")
    
    print("-"*50)
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    
    if failed == 0:
        print("\n所有测试通过! ✓")
    else:
        print(f"\n{failed} 个测试失败，请检查代码。")
    
    return failed == 0

if __name__ == "__main__":
    run_tests()
