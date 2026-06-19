"""
API 集成测试

完整的端到端工作流测试
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.task_service import TaskCreationService, TaskQueryService, TaskMutationService
from app.core.exceptions import ValidationException, NotFoundException
from app.models.task import Task


@pytest.mark.asyncio
class TestTaskWorkflow:
    """完整的任务工作流集成测试"""

    async def test_complete_task_lifecycle(
        self,
        db_session: AsyncSession,
        sample_user_id: str,
        sample_audio_file: str,
    ):
        """测试完整的任务生命周期：创建 → 查询 → 更新 → 完成"""

        # 1. 创建任务
        task = await TaskCreationService.create(
            db=db_session,
            title="完整生命周期测试",
            source_type="upload",
            whisper_model="base",
            output_formats=["txt", "srt"],
            file_path=sample_audio_file,
            source_filename="sample.mp3",
            user_id=uuid4(sample_user_id.encode()),
        )

        assert task.id is not None
        assert task.status == "pending"
        await db_session.commit()

        # 2. 按 ID 查询任务
        retrieved_task = await TaskQueryService.get_by_id(db_session, task.id)
        assert retrieved_task is not None
        assert retrieved_task.title == "完整生命周期测试"

        # 3. 更新任务状态为处理中
        retrieved_task.status = "processing"
        retrieved_task.progress = 0.5
        retrieved_task.progress_message = "正在处理..."
        await db_session.flush()

        # 4. 验证更新
        updated_task = await TaskQueryService.get_by_id(db_session, task.id)
        assert updated_task.status == "processing"
        assert updated_task.progress == 0.5

        # 5. 标记为完成
        updated_task.status = "completed"
        updated_task.progress = 1.0
        await db_session.flush()

        # 6. 最终验证
        final_task = await TaskQueryService.get_by_id(db_session, task.id)
        assert final_task.status == "completed"
        assert final_task.progress == 1.0

    async def test_upload_and_url_task_coexist(
        self,
        db_session: AsyncSession,
        sample_user_id: str,
        sample_audio_file: str,
    ):
        """测试上传任务和 URL 任务可以共存"""

        user_id = uuid4(sample_user_id.encode())

        # 创建上传任务
        upload_task = await TaskCreationService.create(
            db=db_session,
            title="上传任务",
            source_type="upload",
            whisper_model="base",
            output_formats=["srt"],
            file_path=sample_audio_file,
            source_filename="upload.mp3",
            user_id=user_id,
        )

        # 创建 URL 任务
        url_task = await TaskCreationService.create(
            db=db_session,
            title="URL 任务",
            source_type="url",
            whisper_model="base",
            output_formats=["vtt"],
            source_url="https://youtube.com/watch?v=test",
            user_id=user_id,
        )

        await db_session.commit()

        # 验证两个任务都存在且类型不同
        tasks, total = await TaskQueryService.get_by_user(db_session, user_id)
        assert total == 2
        assert len(tasks) == 2

        source_types = {t.source_type for t in tasks}
        assert source_types == {"upload", "url"}

    async def test_task_cancellation_flow(
        self,
        db_session: AsyncSession,
        sample_task: Task,
    ):
        """测试任务取消流程"""

        # 任务初始状态
        assert sample_task.status == "pending"

        # 标记为处理中
        sample_task.status = "processing"
        await db_session.flush()

        # 取消任务
        task = await TaskMutationService.cancel(db_session, sample_task.id)
        assert task.cancel_requested is True

        # 验证可以取消已取消的任务（幂等性）
        task2 = await TaskMutationService.cancel(db_session, sample_task.id)
        assert task2.cancel_requested is True

        # 验证无法取消已完成的任务
        sample_task.status = "completed"
        await db_session.flush()

        with pytest.raises(ValidationException):
            await TaskMutationService.cancel(db_session, sample_task.id)

    async def test_guest_task_daily_limit(
        self,
        db_session: AsyncSession,
        sample_audio_file: str,
    ):
        """测试游客每日任务数限制"""

        client_ip = "192.168.1.100"

        # 创建 3 个游客任务
        for i in range(3):
            await TaskCreationService.create(
                db=db_session,
                title=f"游客任务 {i + 1}",
                source_type="upload",
                whisper_model="base",
                output_formats=["txt"],
                file_path=sample_audio_file,
                source_filename=f"guest{i}.mp3",
                client_ip=client_ip,
            )

        await db_session.commit()

        # 查询今日游客任务数
        count = await TaskQueryService.count_guest_tasks_today(db_session, client_ip)
        assert count == 3

    async def test_user_task_pagination(
        self,
        db_session: AsyncSession,
        sample_user: 'User',
        sample_audio_file: str,
    ):
        """测试用户任务分页"""

        # 创建 25 个任务
        for i in range(25):
            await TaskCreationService.create(
                db=db_session,
                title=f"任务 {i + 1}",
                source_type="upload",
                whisper_model="base",
                output_formats=["srt"],
                file_path=sample_audio_file,
                source_filename=f"task{i}.mp3",
                user_id=sample_user.id,
            )

        await db_session.commit()

        # 第一页（20 条）
        tasks_page1, total = await TaskQueryService.get_by_user(
            db_session,
            sample_user.id,
            page=1,
            page_size=20,
        )
        assert len(tasks_page1) == 20
        assert total == 25

        # 第二页（5 条）
        tasks_page2, _ = await TaskQueryService.get_by_user(
            db_session,
            sample_user.id,
            page=2,
            page_size=20,
        )
        assert len(tasks_page2) == 5

        # 验证顺序（最新的在前）
        first_page_first = tasks_page1[0]
        first_page_last = tasks_page1[-1]
        assert first_page_first.created_at >= first_page_last.created_at

    async def test_task_status_filtering(
        self,
        db_session: AsyncSession,
        sample_user: 'User',
        sample_audio_file: str,
    ):
        """测试按状态过滤任务"""

        # 创建不同状态的任务
        statuses = ["pending", "processing", "completed", "failed", "cancelled"]

        for status in statuses:
            task = await TaskCreationService.create(
                db=db_session,
                title=f"{status} 任务",
                source_type="upload",
                whisper_model="base",
                output_formats=["txt"],
                file_path=sample_audio_file,
                source_filename=f"{status}.mp3",
                user_id=sample_user.id,
            )
            task.status = status
            await db_session.flush()

        await db_session.commit()

        # 按状态过滤
        for status in statuses:
            tasks, total = await TaskQueryService.get_by_user(
                db_session,
                sample_user.id,
                status=status,
            )
            assert total == 1
            assert tasks[0].status == status

    async def test_task_not_found_error(self, db_session: AsyncSession):
        """测试任务不存在时的错误处理"""

        fake_task_id = uuid4()

        # 查询不存在的任务应返回 None
        task = await TaskQueryService.get_by_id(db_session, fake_task_id)
        assert task is None

        # 删除不存在的任务应抛出异常
        with pytest.raises(NotFoundException):
            await TaskMutationService.delete(db_session, fake_task_id)


@pytest.mark.asyncio
class TestTranslationWorkflow:
    """翻译工作流集成测试"""

    async def test_task_with_translation(
        self,
        db_session: AsyncSession,
        sample_user: 'User',
        sample_audio_file: str,
    ):
        """测试带翻译配置的任务创建"""

        task = await TaskCreationService.create(
            db=db_session,
            title="翻译任务",
            source_type="upload",
            whisper_model="base",
            output_formats=["srt", "vtt"],
            translate_target_langs=["zh", "ja", "ko"],
            file_path=sample_audio_file,
            source_filename="translate.mp3",
            user_id=sample_user.id,
        )

        assert task.translate_target_langs == ["zh", "ja", "ko"]
        assert "srt" in task.output_formats
        assert "vtt" in task.output_formats

    async def test_language_validation(
        self,
        db_session: AsyncSession,
        sample_user: 'User',
        sample_audio_file: str,
    ):
        """测试语言代码验证"""

        # 有效的语言代码应该创建成功
        task = await TaskCreationService.create(
            db=db_session,
            title="有效语言",
            source_type="upload",
            whisper_model="base",
            output_formats=["srt"],
            translate_target_langs=["en", "fr", "de"],
            file_path=sample_audio_file,
            source_filename="langs.mp3",
            user_id=sample_user.id,
        )

        assert task.id is not None


@pytest.mark.asyncio
class TestConcurrentOperations:
    """并发操作测试"""

    async def test_concurrent_task_creation(
        self,
        db_session: AsyncSession,
        sample_user: 'User',
        sample_audio_file: str,
    ):
        """测试并发创建任务"""

        import asyncio

        async def create_task(index: int):
            return await TaskCreationService.create(
                db=db_session,
                title=f"并发任务 {index}",
                source_type="upload",
                whisper_model="base",
                output_formats=["txt"],
                file_path=sample_audio_file,
                source_filename=f"concurrent{index}.mp3",
                user_id=sample_user.id,
            )

        # 并发创建 10 个任务
        tasks = await asyncio.gather(
            *[create_task(i) for i in range(10)],
            return_exceptions=True,
        )

        successful = [t for t in tasks if not isinstance(t, Exception)]
        assert len(successful) == 10

        await db_session.commit()

        # 验证所有任务都被创建
        all_tasks, total = await TaskQueryService.get_by_user(db_session, sample_user.id)
        assert total == 10
