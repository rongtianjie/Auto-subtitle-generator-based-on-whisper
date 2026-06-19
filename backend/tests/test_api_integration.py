"""
API 端点集成测试

测试实际的 HTTP 端点和完整的请求/响应流
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.asyncio
class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_health_check(self, client: TestClient):
        """测试基本健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_readiness_check(self, client: TestClient):
        """测试就绪检查"""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]  # 取决于后端服务状态
        data = response.json()
        assert "status" in data
        assert "checks" in data

    def test_sse_connections_stats(self, client: TestClient):
        """测试 SSE 连接统计"""
        response = client.get("/health/sse-connections")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "total_created" in data

    def test_database_stats(self, client: TestClient):
        """测试数据库统计"""
        response = client.get("/health/db-stats")
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "indexes" in data


@pytest.mark.asyncio
class TestTaskCreationAPI:
    """任务创建 API 端点测试"""

    def test_create_task_with_file(self, client: TestClient, sample_audio_file: str):
        """测试文件上传创建任务"""
        with open(sample_audio_file, 'rb') as f:
            files = {'file': f}
            data = {
                'title': 'API 上传测试',
                'source_type': 'upload',
                'whisper_model': 'base',
                'output_formats': ['txt', 'srt'],
            }
            response = client.post("/api/v1/tasks", data=data, files=files)

        assert response.status_code == 201
        task = response.json()
        assert task['title'] == 'API 上传测试'
        assert task['status'] == 'pending'

    def test_create_task_with_url(self, client: TestClient):
        """测试 URL 创建任务"""
        data = {
            'title': 'YouTube 测试',
            'source_type': 'url',
            'source_url': 'https://youtube.com/watch?v=test',
            'whisper_model': 'base',
            'output_formats': ['srt'],
        }
        response = client.post("/api/v1/tasks", json=data)

        assert response.status_code == 201
        task = response.json()
        assert task['source_type'] == 'url'
        assert task['source_url'] == 'https://youtube.com/watch?v=test'

    def test_create_task_validation_error(self, client: TestClient):
        """测试任务创建验证错误"""
        # 缺少必需字段
        data = {'title': 'Invalid Task'}

        response = client.post("/api/v1/tasks", json=data)
        assert response.status_code == 422  # 验证错误

    def test_create_task_without_file(self, client: TestClient):
        """测试上传模式缺少文件"""
        data = {
            'title': 'No File',
            'source_type': 'upload',
            'whisper_model': 'base',
            'output_formats': ['txt'],
        }
        response = client.post("/api/v1/tasks", json=data)

        assert response.status_code == 400
        error = response.json()
        assert error['error_code'] == 'VALIDATION_ERROR'


@pytest.mark.asyncio
class TestTaskQueryAPI:
    """任务查询 API 端点测试"""

    def test_get_task_by_id(self, client: TestClient, sample_task: 'Task'):
        """测试按 ID 获取任务"""
        response = client.get(f"/api/v1/tasks/{sample_task.id}")

        assert response.status_code == 200
        task = response.json()
        assert task['id'] == str(sample_task.id)

    def test_get_nonexistent_task(self, client: TestClient):
        """测试获取不存在的任务"""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = client.get(f"/api/v1/tasks/{fake_id}")
        assert response.status_code == 404

    def test_get_task_outputs(self, client: TestClient, sample_task: 'Task'):
        """测试获取任务输出"""
        response = client.get(f"/api/v1/tasks/{sample_task.id}/outputs")

        assert response.status_code == 200
        outputs = response.json()
        assert isinstance(outputs, list)

    def test_get_queue_status(self, client: TestClient):
        """测试获取队列状态"""
        response = client.get("/api/v1/tasks/queue/status")

        assert response.status_code == 200
        status = response.json()
        assert 'pending_count' in status
        assert 'processing_count' in status
        assert 'avg_duration' in status

    def test_list_tasks_with_pagination(self, client: TestClient):
        """测试分页获取任务列表"""
        response = client.get("/api/v1/tasks?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert 'tasks' in data
        assert 'total' in data
        assert 'page' in data
        assert 'page_size' in data


@pytest.mark.asyncio
class TestTaskMutationAPI:
    """任务修改 API 端点测试"""

    def test_cancel_task(self, client: TestClient, sample_task: 'Task'):
        """测试取消任务"""
        # 先标记为处理中
        response = client.patch(
            f"/api/v1/tasks/{sample_task.id}",
            json={'status': 'processing'}
        )
        assert response.status_code == 200

        # 取消任务
        response = client.post(f"/api/v1/tasks/{sample_task.id}/cancel")
        assert response.status_code == 200
        task = response.json()
        assert task['cancel_requested'] is True

    def test_delete_task(self, client: TestClient, sample_task: 'Task'):
        """测试删除任务"""
        response = client.delete(f"/api/v1/tasks/{sample_task.id}")

        assert response.status_code == 204

        # 验证任务已删除
        response = client.get(f"/api/v1/tasks/{sample_task.id}")
        assert response.status_code == 404

    def test_update_task_progress(self, client: TestClient, sample_task: 'Task'):
        """测试更新任务进度"""
        data = {
            'progress': 0.75,
            'progress_message': '处理中...',
        }
        response = client.patch(f"/api/v1/tasks/{sample_task.id}", json=data)

        assert response.status_code == 200
        task = response.json()
        assert task['progress'] == 0.75
        assert task['progress_message'] == '处理中...'

    def test_complete_task(self, client: TestClient, sample_task: 'Task'):
        """测试标记任务完成"""
        data = {'status': 'completed', 'progress': 1.0}
        response = client.patch(f"/api/v1/tasks/{sample_task.id}", json=data)

        assert response.status_code == 200
        task = response.json()
        assert task['status'] == 'completed'
        assert task['progress'] == 1.0


@pytest.mark.asyncio
class TestErrorHandling:
    """错误处理集成测试"""

    def test_rate_limiting(self, client: TestClient):
        """测试速率限制"""
        # 快速发送多个请求
        for _ in range(10):
            response = client.get("/health")
            # 可能会被限速
            assert response.status_code in [200, 429]

    def test_invalid_json(self, client: TestClient):
        """测试无效 JSON"""
        response = client.post(
            "/api/v1/tasks",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_header(self, client: TestClient):
        """测试缺失必需的请求头"""
        # 某些端点可能需要特定的请求头
        response = client.get("/api/v1/tasks")
        # 不应该返回 400 或 401（取决于认证要求）
        assert response.status_code in [200, 401]

    def test_database_error_handling(self, client: TestClient):
        """测试数据库错误处理"""
        # 尝试访问可能触发数据库错误的端点
        response = client.get("/api/v1/tasks")
        # 应该返回有意义的错误响应
        assert response.status_code in [200, 500, 503]
        if response.status_code >= 500:
            data = response.json()
            assert 'error_code' in data or 'detail' in data


@pytest.mark.asyncio
class TestSSEStream:
    """SSE 流端点测试"""

    def test_sse_connection(self, client: TestClient, sample_task: 'Task'):
        """测试 SSE 连接"""
        response = client.get(
            f"/api/v1/tasks/{sample_task.id}/stream",
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers.get("content-type") == "text/event-stream"

    def test_sse_with_invalid_task(self, client: TestClient):
        """测试无效任务的 SSE 连接"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/v1/tasks/{fake_id}/stream",
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code in [404, 400]


@pytest.mark.asyncio
class TestResponseFormat:
    """响应格式验证测试"""

    def test_task_response_format(self, client: TestClient, sample_task: 'Task'):
        """验证任务响应格式"""
        response = client.get(f"/api/v1/tasks/{sample_task.id}")

        assert response.status_code == 200
        task = response.json()

        # 验证必需字段
        required_fields = [
            'id', 'title', 'source_type', 'whisper_model',
            'status', 'progress', 'created_at'
        ]
        for field in required_fields:
            assert field in task

    def test_error_response_format(self, client: TestClient):
        """验证错误响应格式"""
        response = client.get("/api/v1/tasks/invalid-id")

        assert response.status_code == 404
        error = response.json()

        # 验证错误格式
        assert 'error_code' in error or 'detail' in error

    def test_list_response_format(self, client: TestClient):
        """验证列表响应格式"""
        response = client.get("/api/v1/tasks?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()

        # 验证列表格式
        assert isinstance(data.get('tasks'), list)
        assert 'total' in data
        assert 'page' in data
        assert 'page_size' in data
