"""
性能基准测试工具

使用 locust 进行负载测试和性能分析
"""

from locust import HttpUser, task, between, TaskSet, constant_pacing
from locust.contrib.fasthttp import FastHttpUser
import random
import string


class UserTasks(TaskSet):
    """用户任务集"""

    def on_start(self):
        """用户开始时"""
        # 模拟登录
        response = self.client.post(
            '/api/v1/auth/login',
            json={
                'username': f'test_{random.randint(1000, 9999)}@example.com',
                'password': 'testpass123'
            }
        )
        if response.status_code == 200:
            self.token = response.json()['access_token']
        else:
            self.token = 'test_token'

    def get_headers(self):
        """获取认证头"""
        return {'Authorization': f'Bearer {self.token}'}

    @task(3)
    def get_recent_logs(self):
        """获取最近日志 (高频率)"""
        self.client.get(
            '/api/v1/logs/recent?limit=50',
            headers=self.get_headers(),
            name='/logs/recent'
        )

    @task(2)
    def search_logs(self):
        """搜索日志"""
        keyword = random.choice(['error', 'database', 'request', 'task', 'warning'])
        self.client.get(
            f'/api/v1/logs/search?keyword={keyword}&limit=100',
            headers=self.get_headers(),
            name='/logs/search'
        )

    @task(2)
    def get_error_logs(self):
        """获取错误日志"""
        self.client.get(
            '/api/v1/logs/errors?hours=24&limit=100',
            headers=self.get_headers(),
            name='/logs/errors'
        )

    @task(1)
    def get_log_stats(self):
        """获取日志统计"""
        self.client.get(
            '/api/v1/logs/stats?hours=24',
            headers=self.get_headers(),
            name='/logs/stats'
        )

    @task(2)
    def get_monitoring_metrics(self):
        """获取监控指标"""
        self.client.get(
            '/api/v1/monitoring/metrics',
            headers=self.get_headers(),
            name='/monitoring/metrics'
        )

    @task(1)
    def get_alerts(self):
        """获取告警"""
        self.client.get(
            '/api/v1/monitoring/alerts',
            headers=self.get_headers(),
            name='/monitoring/alerts'
        )

    @task(1)
    def get_health_status(self):
        """获取健康状态"""
        self.client.get('/api/v1/monitoring/health', name='/monitoring/health')

    @task(3)
    def list_tasks(self):
        """获取任务列表"""
        page = random.randint(1, 5)
        self.client.get(
            f'/api/v1/tasks?page={page}&page_size=20',
            headers=self.get_headers(),
            name='/tasks [LIST]'
        )

    @task(1)
    def get_task_details(self):
        """获取任务详情"""
        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=36))
        self.client.get(
            f'/api/v1/tasks/{task_id}',
            headers=self.get_headers(),
            name='/tasks [GET]'
        )

    @task(1)
    def queue_status(self):
        """获取队列状态"""
        self.client.get(
            '/api/v1/tasks/queue/status',
            headers=self.get_headers(),
            name='/tasks/queue/status'
        )


class WebsiteUser(FastHttpUser):
    """Web 用户 - 使用 FastHttpUser 提高性能"""
    wait_time = between(1, 5)
    tasks = [UserTasks]


class AdminUser(FastHttpUser):
    """管理员用户 - 更频繁的操作"""
    wait_time = constant_pacing(2)  # 固定 2 秒间隔
    tasks = [UserTasks]

    def on_start(self):
        """管理员启动时"""
        super().on_start()
        # 获取额外的管理员权限


# Locust 配置
# 运行命令：locust -f locustfile.py --host=http://localhost:8000
