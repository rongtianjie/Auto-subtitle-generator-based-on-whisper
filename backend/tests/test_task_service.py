"""
任务服务单元测试

测试覆盖:
- TaskCreationService: 创建任务、验证参数
- TaskQueryService: 查询任务、统计游客任务
- TaskMutationService: 取消任务、删除任务
- TaskAnalyticsService: 统计数据
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.task_service import (
    TaskCreationService,
    TaskQueryService,
    TaskMutationService,
    TaskAnalyticsService,
)
from app.models.task import Task
from app.core.exceptions import ValidationException, NotFoundException


@pytest.mark.asyncio
class TestTaskCreationService:
    """TaskCreationService 测试"""

    async def test_create_upload_task(self, db_session: AsyncSession):
        """测试创建上传任务"""
        task = await TaskCreationService.create(
            db=db_session,
            title="Test Task",
            source_type="upload",
            whisper_model="base",
            output_formats=["txt", "srt"],
            file_path="/tmp/test.mp3",
            source_filename="test.mp3",
        )

        assert task.id is not None
        assert task.title == "Test Task"
        assert task.source_type == "upload"
        assert task.status == "pending"

    async def test_create_url_task(self, db_session: AsyncSession):
        """测试创建 URL 任务"""
        task = await TaskCreationService.create(
            db=db_session,
            title="URL Task",
            source_type="url",
            whisper_model="small",
            output_formats=["srt", "vtt"],
            source_url="https://youtube.com/watch?v=123",
        )

        assert task.source_type == "url"
        assert task.source_url == "https://youtube.com/watch?v=123"

    async def test_create_invalid_source_type(self, db_session: AsyncSession):
        """测试无效的 source_type"""
        with pytest.raises(ValidationException):
            await TaskCreationService.create(
                db=db_session,
                title="Invalid",
                source_type="invalid",
                whisper_model="base",
                output_formats=["txt"],
            )

    async def test_create_upload_without_file(self, db_session: AsyncSession):
        """测试上传模式缺少文件"""
        with pytest.raises(ValidationException):
            await TaskCreationService.create(
                db=db_session,
                title="No File",
                source_type="upload",
                whisper_model="base",
                output_formats=["txt"],
            )

    async def test_create_url_without_source_url(self, db_session: AsyncSession):
        """测试 URL 模式缺少 source_url"""
        with pytest.raises(ValidationException):
            await TaskCreationService.create(
                db=db_session,
                title="No URL",
                source_type="url",
                whisper_model="base",
                output_formats=["txt"],
            )


@pytest.mark.asyncio
class TestTaskQueryService:
    """TaskQueryService 测试"""

    async def test_get_task_by_id(self, db_session: AsyncSession, sample_task: Task):
        """测试按 ID 查询任务"""
        task = await TaskQueryService.get_by_id(db_session, sample_task.id)
        assert task is not None
        assert task.id == sample_task.id

    async def test_get_nonexistent_task(self, db_session: AsyncSession):
        """测试查询不存在的任务"""
        task = await TaskQueryService.get_by_id(db_session, uuid4())
        assert task is None

    async def test_get_user_tasks(self, db_session: AsyncSession, sample_user_id):
        """测试获取用户任务列表"""
        # 创建几个任务
        for i in range(3):
            await TaskCreationService.create(
                db=db_session,
                title=f"Task {i}",
                source_type="upload",
                whisper_model="base",
                output_formats=["txt"],
                file_path=f"/tmp/test{i}.mp3",
                user_id=sample_user_id,
            )

        await db_session.commit()

        tasks, total = await TaskQueryService.get_by_user(
            db_session, sample_user_id, page=1, page_size=10
        )

        assert len(tasks) == 3
        assert total == 3

    async def test_count_guest_tasks_today(self, db_session: AsyncSession):
        """测试统计游客今日任务"""
        client_ip = "192.168.1.1"

        # 创建几个游客任务
        for i in range(2):
            await TaskCreationService.create(
                db=db_session,
                title=f"Guest Task {i}",
                source_type="upload",
                whisper_model="base",
                output_formats=["txt"],
                file_path=f"/tmp/guest{i}.mp3",
                client_ip=client_ip,
            )

        await db_session.commit()

        count = await TaskQueryService.count_guest_tasks_today(db_session, client_ip)
        assert count == 2


@pytest.mark.asyncio
class TestTaskMutationService:
    """TaskMutationService 测试"""

    async def test_cancel_queued_task(self, db_session: AsyncSession, sample_task: Task):
        """测试取消排队中的任务"""
        sample_task.status = "queued"
        await db_session.flush()

        task = await TaskMutationService.cancel(db_session, sample_task.id)
        assert task.cancel_requested is True

    async def test_cancel_processing_task(self, db_session: AsyncSession, sample_task: Task):
        """测试取消处理中的任务"""
        sample_task.status = "processing"
        await db_session.flush()

        task = await TaskMutationService.cancel(db_session, sample_task.id)
        assert task.cancel_requested is True

    async def test_cannot_cancel_completed_task(
        self, db_session: AsyncSession, sample_task: Task
    ):
        """测试无法取消已完成的任务"""
        sample_task.status = "completed"
        await db_session.flush()

        with pytest.raises(ValidationException):
            await TaskMutationService.cancel(db_session, sample_task.id)

    async def test_cancel_nonexistent_task(self, db_session: AsyncSession):
        """测试取消不存在的任务"""
        with pytest.raises(NotFoundException):
            await TaskMutationService.cancel(db_session, uuid4())

    async def test_delete_task(self, db_session: AsyncSession, sample_task: Task):
        """测试删除任务"""
        task_id = sample_task.id
        await TaskMutationService.delete(db_session, task_id)

        await db_session.commit()

        # 验证任务已删除
        task = await TaskQueryService.get_by_id(db_session, task_id)
        assert task is None


@pytest.mark.asyncio
class TestTaskAnalyticsService:
    """TaskAnalyticsService 测试"""

    async def test_get_user_stats(self, db_session: AsyncSession, sample_user_id):
        """测试获取用户统计"""
        # 创建几个任务
        task1 = await TaskCreationService.create(
            db=db_session,
            title="Task 1",
            source_type="upload",
            whisper_model="base",
            output_formats=["txt"],
            file_path="/tmp/test1.mp3",
            user_id=sample_user_id,
        )
        task2 = await TaskCreationService.create(
            db=db_session,
            title="Task 2",
            source_type="upload",
            whisper_model="base",
            output_formats=["txt"],
            file_path="/tmp/test2.mp3",
            user_id=sample_user_id,
        )

        # 标记一个为完成
        task1.status = "completed"
        await db_session.flush()

        stats = await TaskAnalyticsService.get_user_stats(db_session, sample_user_id)

        assert stats["total"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 0
        assert stats["success_rate"] == 50.0

    async def test_get_platform_stats(self, db_session: AsyncSession):
        """测试获取平台统计"""
        stats = await TaskAnalyticsService.get_platform_stats(db_session)

        assert "total" in stats
        assert "completed" in stats
        assert "processing" in stats
        assert "queued" in stats
