#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评论功能验证脚本
直接使用 FastAPI TestClient 测试核心功能
"""

import sys
import os
from datetime import datetime

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db import Base
from app.deps import get_db
from app.main import app

# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test_validation.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """依赖注入覆盖 - 使用测试数据库"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


class CommentFeatureValidator:
    """评论功能验证器"""
    
    def __init__(self):
        self.client = None
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def setup(self):
        """初始化测试环境"""
        print("\n" + "="*60)
        print("初始化测试环境...")
        print("="*60)
        
        # 创建测试数据库表
        Base.metadata.create_all(bind=engine)
        
        # 覆盖依赖
        app.dependency_overrides[get_db] = override_get_db
        
        # 创建测试客户端
        self.client = TestClient(app)
        
        print("✓ 测试环境初始化完成")
        print(f"✓ 测试数据库: {TEST_DATABASE_URL}")
    
    def teardown(self):
        """清理测试环境"""
        print("\n" + "="*60)
        print("清理测试环境...")
        print("="*60)
        
        # 清理依赖覆盖
        app.dependency_overrides.clear()
        
        # 关闭数据库连接
        engine.dispose()
        
        # 删除测试数据库文件
        if os.path.exists("test_validation.db"):
            os.remove("test_validation.db")
            print("✓ 测试数据库已删除")
        
        print("✓ 测试环境清理完成")
    
    def log(self, test_name, success, message=""):
        """记录测试结果"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if success:
            self.passed += 1
            status = "✓ 通过"
            print(f"[{timestamp}] {test_name}: {status}")
        else:
            self.failed += 1
            status = "✗ 失败"
            print(f"[{timestamp}] {test_name}: {status}")
            if message:
                print(f"    错误信息: {message}")
        
        self.results.append({
            "name": test_name,
            "success": success,
            "message": message,
            "timestamp": timestamp
        })
    
    def register_and_login(self, email, password="password123"):
        """注册并登录用户，返回认证头"""
        # 注册
        self.client.post("/auth/register", json={"email": email, "password": password})
        
        # 登录
        login_response = self.client.post(
            "/auth/login",
            data={"username": email, "password": password}
        )
        
        if login_response.status_code != 200:
            return None
        
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("开始测试评论功能...")
        print("="*60)
        
        # 测试1: 健康检查
        self.test_health_check()
        
        # 测试2: 用户注册和登录
        self.test_user_auth()
        
        # 测试3: 创建任务
        self.test_create_task()
        
        # 测试4: 创建评论
        self.test_create_comment()
        
        # 测试5: 获取评论列表
        self.test_get_comments()
        
        # 测试6: 评论分页
        self.test_comment_pagination()
        
        # 测试7: 更新评论
        self.test_update_comment()
        
        # 测试8: 删除评论
        self.test_delete_comment()
        
        # 测试9: 权限控制 - 不能修改他人评论
        self.test_update_other_comment()
        
        # 测试10: 权限控制 - 不能删除他人评论
        self.test_delete_other_comment()
        
        # 测试11: 参数校验
        self.test_parameter_validation()
        
        # 输出汇总
        self.print_summary()
    
    def test_health_check(self):
        """测试1: 健康检查"""
        test_name = "1. 健康检查"
        try:
            response = self.client.get("/health")
            if response.status_code == 200 and response.json() == {"status": "ok"}:
                self.log(test_name, True)
            else:
                self.log(test_name, False, f"状态码: {response.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_user_auth(self):
        """测试2: 用户注册和登录"""
        test_name = "2. 用户注册和登录"
        try:
            headers = self.register_and_login("testuser@example.com")
            if headers and "Authorization" in headers:
                self.log(test_name, True)
            else:
                self.log(test_name, False, "登录失败")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_create_task(self):
        """测试3: 创建任务"""
        test_name = "3. 创建任务"
        try:
            headers = self.register_and_login("taskuser@example.com")
            response = self.client.post(
                "/tasks",
                json={"title": "测试任务", "description": "用于测试评论功能"},
                headers=headers
            )
            if response.status_code == 201:
                data = response.json()
                self.log(test_name, True, f"任务ID: {data['id']}")
            else:
                self.log(test_name, False, f"状态码: {response.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_create_comment(self):
        """测试4: 创建评论"""
        test_name = "4. 创建评论"
        try:
            headers = self.register_and_login("commentuser@example.com")
            
            # 先创建任务
            task_response = self.client.post(
                "/tasks",
                json={"title": "评论测试任务"},
                headers=headers
            )
            task_id = task_response.json()["id"]
            
            # 创建评论
            comment_response = self.client.post(
                f"/tasks/{task_id}/comments",
                json={"content": "这是一条测试评论"},
                headers=headers
            )
            
            if comment_response.status_code == 201:
                data = comment_response.json()
                self.log(test_name, True, f"评论ID: {data['id']}, 内容: '{data['content']}'")
            else:
                self.log(test_name, False, f"状态码: {comment_response.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_get_comments(self):
        """测试5: 获取评论列表"""
        test_name = "5. 获取评论列表"
        try:
            headers = self.register_and_login("getcomments@example.com")
            
            # 先创建任务
            task_response = self.client.post(
                "/tasks",
                json={"title": "获取评论测试任务"},
                headers=headers
            )
            task_id = task_response.json()["id"]
            
            # 创建多条评论
            for i in range(3):
                self.client.post(
                    f"/tasks/{task_id}/comments",
                    json={"content": f"评论 {i+1}"},
                    headers=headers
                )
            
            # 获取评论列表
            response = self.client.get(f"/tasks/{task_id}/comments", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                expected_keys = ["items", "total", "skip", "limit"]
                if all(key in data for key in expected_keys):
                    self.log(
                        test_name, 
                        True, 
                        f"总条数: {data['total']}, 当前页: {len(data['items'])}条, skip={data['skip']}, limit={data['limit']}"
                    )
                else:
                    self.log(test_name, False, f"响应缺少必要字段: {data.keys()}")
            else:
                self.log(test_name, False, f"状态码: {response.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_comment_pagination(self):
        """测试6: 评论分页"""
        test_name = "6. 评论分页"
        try:
            headers = self.register_and_login("pagination@example.com")
            
            # 先创建任务
            task_response = self.client.post(
                "/tasks",
                json={"title": "分页测试任务"},
                headers=headers
            )
            task_id = task_response.json()["id"]
            
            # 创建25条评论
            for i in range(25):
                self.client.post(
                    f"/tasks/{task_id}/comments",
                    json={"content": f"评论 {i+1}"},
                    headers=headers
                )
            
            # 测试默认分页（前20条）
            response1 = self.client.get(f"/tasks/{task_id}/comments", headers=headers)
            data1 = response1.json()
            
            # 测试第二页
            response2 = self.client.get(f"/tasks/{task_id}/comments?skip=20&limit=20", headers=headers)
            data2 = response2.json()
            
            # 测试自定义limit
            response3 = self.client.get(f"/tasks/{task_id}/comments?skip=0&limit=5", headers=headers)
            data3 = response3.json()
            
            if (response1.status_code == 200 and response2.status_code == 200 and response3.status_code == 200):
                if (data1["total"] == 25 and len(data1["items"]) == 20 and
                    len(data2["items"]) == 5 and len(data3["items"]) == 5):
                    self.log(
                        test_name,
                        True,
                        f"总条数: 25, 第一页: {len(data1['items'])}条, 第二页: {len(data2['items'])}条, 自定义limit=5: {len(data3['items'])}条"
                    )
                else:
                    self.log(test_name, False, f"分页数据不正确: total={data1['total']}, items1={len(data1['items'])}, items2={len(data2['items'])}")
            else:
                self.log(test_name, False, f"状态码错误: 第一页={response1.status_code}, 第二页={response2.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_update_comment(self):
        """测试7: 更新评论"""
        test_name = "7. 更新评论"
        try:
            headers = self.register_and_login("updateuser@example.com")
            
            # 先创建任务
            task_response = self.client.post(
                "/tasks",
                json={"title": "更新评论测试任务"},
                headers=headers
            )
            task_id = task_response.json()["id"]
            
            # 创建评论
            create_response = self.client.post(
                f"/tasks/{task_id}/comments",
                json={"content": "原始内容"},
                headers=headers
            )
            comment_id = create_response.json()["id"]
            original_updated_at = create_response.json()["updated_at"]
            
            # 更新评论
            update_response = self.client.patch(
                f"/comments/{comment_id}",
                json={"content": "更新后的内容"},
                headers=headers
            )
            
            if update_response.status_code == 200:
                data = update_response.json()
                if data["content"] == "更新后的内容" and data["updated_at"] != original_updated_at:
                    self.log(
                        test_name,
                        True,
                        f"评论ID: {comment_id}, 原始内容: '原始内容', 更新后: '{data['content']}'"
                    )
                else:
                    self.log(test_name, False, f"更新内容不正确: {data['content']}")
            else:
                self.log(test_name, False, f"状态码: {update_response.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_delete_comment(self):
        """测试8: 删除评论"""
        test_name = "8. 删除评论"
        try:
            headers = self.register_and_login("deleteuser@example.com")
            
            # 先创建任务
            task_response = self.client.post(
                "/tasks",
                json={"title": "删除评论测试任务"},
                headers=headers
            )
            task_id = task_response.json()["id"]
            
            # 创建评论
            create_response = self.client.post(
                f"/tasks/{task_id}/comments",
                json={"content": "要删除的评论"},
                headers=headers
            )
            comment_id = create_response.json()["id"]
            
            # 删除评论
            delete_response = self.client.delete(f"/comments/{comment_id}", headers=headers)
            
            # 验证是否已删除
            get_response = self.client.get(f"/tasks/{task_id}/comments", headers=headers)
            comments_data = get_response.json()
            
            if delete_response.status_code == 204 and comments_data["total"] == 0:
                self.log(
                    test_name,
                    True,
                    f"评论ID: {comment_id} 已删除, 当前评论数: {comments_data['total']}"
                )
            else:
                self.log(test_name, False, f"删除状态码: {delete_response.status_code}, 剩余评论数: {comments_data['total']}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_update_other_comment(self):
        """测试9: 权限控制 - 不能修改他人评论"""
        test_name = "9. 权限控制 - 不能修改他人评论"
        try:
            # 用户1创建评论
            headers1 = self.register_and_login("user1_perm@example.com")
            task_response = self.client.post(
                "/tasks",
                json={"title": "权限测试任务"},
                headers=headers1
            )
            task_id = task_response.json()["id"]
            
            create_response = self.client.post(
                f"/tasks/{task_id}/comments",
                json={"content": "用户1的评论"},
                headers=headers1
            )
            comment_id = create_response.json()["id"]
            
            # 用户2尝试修改用户1的评论
            headers2 = self.register_and_login("user2_perm@example.com")
            update_response = self.client.patch(
                f"/comments/{comment_id}",
                json={"content": "被篡改的内容"},
                headers=headers2
            )
            
            if update_response.status_code == 403:
                self.log(
                    test_name,
                    True,
                    f"用户2尝试修改用户1的评论, 状态码: {update_response.status_code} (预期403)"
                )
            else:
                self.log(test_name, False, f"预期状态码403, 实际: {update_response.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_delete_other_comment(self):
        """测试10: 权限控制 - 不能删除他人评论"""
        test_name = "10. 权限控制 - 不能删除他人评论"
        try:
            # 用户1创建评论
            headers1 = self.register_and_login("user1_del@example.com")
            task_response = self.client.post(
                "/tasks",
                json={"title": "删除权限测试任务"},
                headers=headers1
            )
            task_id = task_response.json()["id"]
            
            create_response = self.client.post(
                f"/tasks/{task_id}/comments",
                json={"content": "用户1的评论"},
                headers=headers1
            )
            comment_id = create_response.json()["id"]
            
            # 用户2尝试删除用户1的评论
            headers2 = self.register_and_login("user2_del@example.com")
            delete_response = self.client.delete(f"/comments/{comment_id}", headers=headers2)
            
            if delete_response.status_code == 403:
                self.log(
                    test_name,
                    True,
                    f"用户2尝试删除用户1的评论, 状态码: {delete_response.status_code} (预期403)"
                )
            else:
                self.log(test_name, False, f"预期状态码403, 实际: {delete_response.status_code}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def test_parameter_validation(self):
        """测试11: 参数校验"""
        test_name = "11. 参数校验"
        try:
            headers = self.register_and_login("validation@example.com")
            
            # 创建任务和评论
            task_response = self.client.post(
                "/tasks",
                json={"title": "参数校验测试任务"},
                headers=headers
            )
            task_id = task_response.json()["id"]
            
            # 测试无效的分页参数
            test_cases = [
                ("skip=-1", "skip为负数"),
                ("limit=0", "limit为0"),
                ("limit=-5", "limit为负数"),
                ("limit=101", "limit超过100"),
            ]
            
            all_passed = True
            failed_cases = []
            
            for params, desc in test_cases:
                response = self.client.get(
                    f"/tasks/{task_id}/comments?{params}",
                    headers=headers
                )
                if response.status_code != 422:
                    all_passed = False
                    failed_cases.append(f"{desc}: 预期422, 实际{response.status_code}")
            
            # 测试有效的参数
            valid_response = self.client.get(
                f"/tasks/{task_id}/comments?skip=0&limit=100",
                headers=headers
            )
            
            if all_passed and valid_response.status_code == 200:
                self.log(
                    test_name,
                    True,
                    f"所有无效参数都返回422, 有效参数返回{valid_response.status_code}"
                )
            else:
                self.log(test_name, False, f"失败用例: {'; '.join(failed_cases)}")
        except Exception as e:
            self.log(test_name, False, str(e))
    
    def print_summary(self):
        """打印测试汇总"""
        print("\n" + "="*60)
        print("测试结果汇总")
        print("="*60)
        
        total = self.passed + self.failed
        print(f"\n总计: {total} 个测试")
        print(f"通过: {self.passed} 个 ✓")
        print(f"失败: {self.failed} 个 ✗")
        
        if self.failed == 0:
            print("\n" + "="*60)
            print("🎉 所有测试通过！评论功能工作正常！")
            print("="*60)
        else:
            print("\n" + "="*60)
            print(f"⚠️  {self.failed} 个测试失败，请检查代码")
            print("="*60)
            
            print("\n失败的测试:")
            for result in self.results:
                if not result["success"]:
                    print(f"  - {result['name']}: {result['message']}")
        
        return self.failed == 0


def main():
    """主函数"""
    print("\n" + "#"*60)
    print("# 评论功能验证脚本")
    print("# 直接使用 FastAPI TestClient 测试核心功能")
    print("#"*60)
    
    validator = CommentFeatureValidator()
    
    try:
        # 初始化
        validator.setup()
        
        # 运行所有测试
        validator.run_all_tests()
        
        # 返回测试结果
        return validator.failed == 0
        
    finally:
        # 清理
        validator.teardown()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
