import os
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.task_output import TaskOutput
from app.core.task_queue import task_queue
from app.core.storage import storage
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)


class TaskCreationService:
    """任务创建服务"""

    @staticmethod
    async def create(
        db: AsyncSession,
        title: str,
        source_type: str,
        whisper_model: str,
        output_formats: list,
        translate_target_langs: list | None = None,
        source_url: str | None = None,
        source_filename: str | None = None,
        file_path: str | None = None,
        user_id: UUID | None = None,
        client_ip: str | None = None,
    ) -> Task:
        """创建新任务"""
        # 验证参数
        if source_type not in ("upload", "url"):
            raise ValidationException("source_type 必须是 upload 或 url")

        if source_type == "upload" and not file_path:
            raise ValidationException("上传模式必须提供文件")

        if source_type == "url" and not source_url:
            raise ValidationException("URL 模式必须提供 source_url")

        # 创建任务
        task = Task(
            user_id=user_id,
            title=title or source_filename or "未命名任务",
            source_type=source_type,
            source_url=source_url,
            source_filename=source_filename,
            file_path=file_path,
            whisper_model=whisper_model,
            output_formats=output_formats,
            translate_target_langs=translate_target_langs,
            client_ip=client_ip,
            status="pending",
        )
        db.add(task)
        await db.flush()
        await task_queue.enqueue(task.id, db)
        return task


class TaskQueryService:
    """任务查询服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: UUID) -> Task | None:
        """获取单个任务"""
        result = await db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_user(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Task], int]:
        """获取用户的任务列表"""
        query = select(Task).where(Task.user_id == user_id)
        count_query = select(func.count(Task.id)).where(Task.user_id == user_id)

        if status:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(desc(Task.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get_outputs(db: AsyncSession, task_id: UUID) -> list[TaskOutput]:
        """获取任务的输出文件"""
        result = await db.execute(
            select(TaskOutput).where(TaskOutput.task_id == task_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_guest_tasks_today(db: AsyncSession, client_ip: str) -> int:
        """查询游客今日任务数"""
        result = await db.execute(
            select(func.count(Task.id)).where(
                Task.client_ip == client_ip,
                func.date(Task.created_at) == func.current_date(),
            )
        )
        return result.scalar() or 0


class TaskMutationService:
    """任务修改服务"""

    @staticmethod
    async def cancel(db: AsyncSession, task_id: UUID) -> Task:
        """取消任务"""
        task = await TaskQueryService.get_by_id(db, task_id)
        if not task:
            raise NotFoundException("Task", str(task_id))

        if task.status not in ("queued", "processing"):
            raise ValidationException("只能取消排队或处理中的任务")

        task.cancel_requested = True
        task.progress_message = "正在等待当前阶段结束..."
        await db.flush()
        return task

    @staticmethod
    async def delete(db: AsyncSession, task_id: UUID) -> None:
        """删除任务及其文件"""
        task = await TaskQueryService.get_by_id(db, task_id)
        if not task:
            raise NotFoundException("Task", str(task_id))

        storage.delete_task_files(task_id)
        await db.delete(task)
        await task_queue.update_queue_positions(db)


class TaskAnalyticsService:
    """任务统计分析服务"""

    @staticmethod
    async def get_user_stats(db: AsyncSession, user_id: UUID) -> dict:
        """获取用户的任务统计"""
        total = await db.scalar(
            select(func.count(Task.id)).where(Task.user_id == user_id)
        ) or 0

        completed = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == "completed"
            )
        ) or 0

        failed = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == "failed"
            )
        ) or 0

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total * 100) if total > 0 else 0,
        }

    @staticmethod
    async def get_platform_stats(db: AsyncSession) -> dict:
        """获取平台的任务统计"""
        total = await db.scalar(select(func.count(Task.id))) or 0
        completed = await db.scalar(
            select(func.count(Task.id)).where(Task.status == "completed")
        ) or 0
        processing = await db.scalar(
            select(func.count(Task.id)).where(Task.status == "processing")
        ) or 0
        queued = await db.scalar(
            select(func.count(Task.id)).where(Task.status == "queued")
        ) or 0

        return {
            "total": total,
            "completed": completed,
            "processing": processing,
            "queued": queued,
        }


# 向后兼容的服务实例
class TaskService:
    """任务服务（向后兼容）"""

    create_task = TaskCreationService.create
    get_task = TaskQueryService.get_by_id
    get_user_tasks = TaskQueryService.get_by_user
    get_task_outputs = TaskQueryService.get_outputs
    count_guest_tasks_today = TaskQueryService.count_guest_tasks_today
    cancel_task = TaskMutationService.cancel
    delete_task = TaskMutationService.delete


task_service = TaskService()
