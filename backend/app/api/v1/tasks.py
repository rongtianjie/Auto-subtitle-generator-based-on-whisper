import json
import os
import asyncio
import shutil
import uuid
import time
from typing import Any
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, status, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse
from loguru import logger

from app.database import get_db, get_fresh_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskOutputResponse,
    TaskListResponse,
    QueueStatusResponse,
    TaskUpdateRequest,
)
from app.services.task_service import task_service
from app.services.config_service import get_config_value
from app.core.task_queue import task_queue
from app.core.storage import storage
from app.core.rate_limiter import upload_rate_limiter
from app.core.validators import validate_upload
from app.config import settings
from app.core.exceptions import (
    ValidationException,
    FileTooLargeException,
    NotFoundException,
    QuotaExceededException,
    OperationNotAllowedException,
    ForbiddenException,
    UnauthorizedException,
    TooManyRequestsException,
)
from app.core.sse_manager import sse_manager

router = APIRouter(prefix="/tasks", tags=["任务"])


def _parse_task_id(task_id: str) -> UUID:
    """将字符串任务 ID 解析为 UUID，非法值视为未找到。"""
    try:
        return UUID(task_id)
    except (TypeError, ValueError) as exc:
        raise NotFoundException(resource="Task", identifier=task_id) from exc


def _parse_json_list_field(value: Any, field_name: str) -> list[str]:
    """兼容 JSON 字符串和单值表单字段的列表解析。"""
    if value is None:
        raise ValidationException(detail=f"{field_name} 不能为空")

    if isinstance(value, list):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [value]
    else:
        raise ValidationException(detail=f"{field_name} 格式无效")

    if isinstance(parsed, str):
        parsed = [parsed]

    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValidationException(detail=f"{field_name} 格式无效")

    return parsed


def _task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=str(task.id),
        user_id=str(task.user_id) if task.user_id else None,
        title=task.title,
        source_type=task.source_type,
        source_url=task.source_url,
        source_filename=task.source_filename,
        whisper_model=task.whisper_model,
        output_formats=task.output_formats,
        translate_target_langs=task.translate_target_langs,
        status=task.status,
        progress=task.progress,
        progress_message=task.progress_message,
        queue_position=task.queue_position,
        estimated_seconds=task.estimated_seconds,
        error_message=task.error_message,
        cancel_requested=task.cancel_requested,
        created_at=str(task.created_at),
        started_at=str(task.started_at) if task.started_at else None,
        completed_at=str(task.completed_at) if task.completed_at else None,
    )


@router.get("/defaults")
async def get_task_defaults(db: AsyncSession = Depends(get_db)):
    """获取创建任务的默认配置（公开接口，无需登录）"""
    default_model = await get_config_value(db, "default_whisper_model", "base")
    return {"default_whisper_model": default_model}


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    source_type: str = Form(...),
    source_url: str = Form(None),
    title: str = Form(None),
    whisper_model: str = Form("base"),
    output_formats: str = Form('["txt","srt","bilingual_srt"]'),
    translate_target_langs: str = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
    request: Request = None,
):
    """创建任务：支持上传文件或提交 URL"""
    parsed_formats = _parse_json_list_field(output_formats, "output_formats")
    parsed_langs = None
    if translate_target_langs:
        parsed_langs = _parse_json_list_field(translate_target_langs, "translate_target_langs")

    file_path = None
    source_filename = None

    if source_type == "upload":
        if not file:
            raise ValidationException(message="上传模式需要提供文件")

        # 获取客户端 IP 用于速率限制
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host

        # 检查上传频率限制
        allowed, remaining = upload_rate_limiter.is_allowed(f"upload:{client_ip}")
        if not allowed:
            raise TooManyRequestsException(
                message="上传过于频繁，请稍后再试",
                retry_after=60
            )

        # 验证文件（清理文件名、验证 MIME 类型）
        validated_filename = validate_upload(file.filename, file.content_type)

        # 校验文件大小
        max_file_size_mb = await get_config_value(db, "max_file_size_mb", settings.MAX_FILE_SIZE_MB)
        max_size_bytes = max_file_size_mb * 1024 * 1024

        # 检查 Content-Length 头（快速拒绝）
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_size_bytes:
            raise FileTooLargeException(max_size_mb=max_file_size_mb)

        # 检查实际文件大小（seek 到末尾获取大小）
        file.file.seek(0, 2)
        actual_size = file.file.tell()
        file.file.seek(0)
        if actual_size > max_size_bytes:
            raise FileTooLargeException(max_size_mb=max_file_size_mb)

        # 流式写入，避免将整个文件加载到内存
        temp_id = uuid.uuid4()
        file_path = storage.save_upload_stream(temp_id, validated_filename, file.file)
        source_filename = validated_filename
        title = title or validated_filename

    # --- 游客任务次数限制校验 ---
    if current_user is None:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host

        guest_limit = await get_config_value(db, "guest_task_limit", 3)
        today_count = await task_service.count_guest_tasks_today(db, client_ip)

        if today_count >= guest_limit:
            raise QuotaExceededException(message="今日任务已达上限，请登录后继续使用")
    else:
        client_ip = None
    # --- 校验结束 ---

    task = await task_service.create_task(
        db=db,
        title=title or "未命名任务",
        source_type=source_type,
        whisper_model=whisper_model,
        output_formats=parsed_formats,
        translate_target_langs=parsed_langs,
        source_url=source_url,
        source_filename=source_filename,
        file_path=file_path,
        user_id=current_user.id if current_user else None,
        client_ip=client_ip,
    )

    # 如果上传文件，需要更新 file_path 到正确的 task_id 目录
    if source_type == "upload" and file_path:
        old_dir = Path(file_path).parent
        new_path = storage.get_upload_path(task.id, source_filename)
        # 确保目标目录存在
        Path(new_path).parent.mkdir(parents=True, exist_ok=True)
        # 移动文件
        shutil.move(file_path, new_path)
        task.file_path = new_path
        # 清理临时目录
        if old_dir.exists():
            shutil.rmtree(old_dir)
        await db.flush()

    return _task_to_response(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """获取任务列表（未登录时返回空列表）"""
    # 未登录用户返回空列表
    if not current_user:
        return TaskListResponse(
            tasks=[],
            total=0,
            page=page,
            page_size=page_size,
        )

    tasks, total = await task_service.get_user_tasks(db, current_user.id, page, page_size, status)
    return TaskListResponse(
        tasks=[_task_to_response(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/queue", response_model=QueueStatusResponse)
async def get_queue_status(db: AsyncSession = Depends(get_db)):
    info = await task_queue.get_queue_info(db)
    return QueueStatusResponse(**info)


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status_alias(db: AsyncSession = Depends(get_db)):
    return await get_queue_status(db)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    parsed_task_id = _parse_task_id(task_id)
    task = await task_service.get_task(db, parsed_task_id)
    if not task:
        raise NotFoundException(resource="Task", identifier=task_id)
    return _task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    payload: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    parsed_task_id = _parse_task_id(task_id)
    task = await task_service.get_task(db, parsed_task_id)
    if not task:
        raise NotFoundException(resource="Task", identifier=task_id)

    if current_user and task.user_id and task.user_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权修改此任务")
    if not current_user and task.user_id is not None:
        raise ForbiddenException("无权修改此任务")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(task, field_name, value)

    if "status" in updates and updates["status"] == "completed":
        task.progress = 1.0 if payload.progress is None else payload.progress
    if "status" in updates and updates["status"] in {"processing", "queued"} and task.progress is None:
        task.progress = 0.0

    await db.flush()
    return _task_to_response(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    parsed_task_id = _parse_task_id(task_id)
    task = await task_service.get_task(db, parsed_task_id)
    if not task:
        raise NotFoundException(resource="Task", identifier=task_id)
    if current_user is None:
        raise UnauthorizedException("删除任务需要登录")
    if task.user_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权删除此任务")
    await task_service.delete_task(db, parsed_task_id)
    return Response(status_code=204)


@router.get("/{task_id}/outputs", response_model=list[TaskOutputResponse])
async def get_task_outputs(task_id: str, db: AsyncSession = Depends(get_db)):
    parsed_task_id = _parse_task_id(task_id)
    outputs = await task_service.get_task_outputs(db, parsed_task_id)
    return [
        TaskOutputResponse(
            id=str(o.id),
            task_id=str(o.task_id),
            format_type=o.format_type,
            language_pair=o.language_pair,
            file_path=o.file_path,
            file_size=o.file_size,
            created_at=str(o.created_at),
        )
        for o in outputs
    ]


@router.put("/{task_id}/cancel")
@router.post("/{task_id}/cancel")
async def cancel_own_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """取消自己的任务"""
    parsed_task_id = _parse_task_id(task_id)
    result = await db.execute(select(Task).where(Task.id == parsed_task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException(resource="Task", identifier=task_id)

    # 任务所有者或管理员可以取消
    if current_user and task.user_id and task.user_id != current_user.id:
        if current_user.role != "admin":
            raise ForbiddenException("无权取消此任务")
    elif not current_user and task.user_id is not None:
        raise ForbiddenException("无权取消此任务")

    if task.status not in ("queued", "processing"):
        raise OperationNotAllowedException("只能取消正在处理或排队中的任务")

    task = await task_service.cancel_task(db, parsed_task_id)
    await task_queue.update_queue_positions(db)
    await db.commit()
    return _task_to_response(task)


@router.get("/{task_id}/outputs/{output_id}/download")
async def download_task_output(
    task_id: str,
    output_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """下载任务输出文件"""
    from app.models.task_output import TaskOutput
    from sqlalchemy import select

    parsed_task_id = _parse_task_id(task_id)
    result = await db.execute(
        select(TaskOutput).where(TaskOutput.id == output_id, TaskOutput.task_id == parsed_task_id)
    )
    output = result.scalar_one_or_none()
    if not output:
        raise NotFoundException(resource="Output", identifier=str(output_id))

    file_path = output.file_path
    if not os.path.exists(file_path):
        raise NotFoundException(resource="File", identifier=str(output_id))

    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{task_id}/stream")
async def stream_task_progress(task_id: str, db: AsyncSession = Depends(get_fresh_db)):
    """SSE 实时进度推送

    使用独立的数据库会话，避免会话缓存导致进度数据不更新

    连接管理:
    - 30 秒无数据则认为连接已死亡并关闭
    - 每 10 秒发送心跳包 (keepalive event)
    - 自动清理超时的连接
    """
    import uuid as uuid_module
    from app.core.sse_manager import sse_manager

    parsed_task_id = _parse_task_id(task_id)
    connection_id = str(uuid_module.uuid4())
    sse_manager.register(connection_id, str(parsed_task_id))
    last_heartbeat = time.time()
    heartbeat_interval = 10  # 每 10 秒发送一次心跳

    async def event_generator():
        try:
            while True:
                # 检查是否需要清理空闲连接
                if sse_manager.should_cleanup():
                    cleaned = sse_manager.cleanup_idle()
                    if cleaned > 0:
                        logger.debug(f"Cleaned {cleaned} idle SSE connections")
                    sse_manager.mark_cleanup()

                try:
                    task = await task_service.get_task(db, parsed_task_id)
                    if not task:
                        yield {
                            "event": "error",
                            "data": json.dumps({"message": "任务不存在"}),
                        }
                        break

                    await db.refresh(task)

                    # 更新连接活动时间
                    sse_manager.update_activity(connection_id)

                    # 发送进度数据
                    data = {
                        "status": task.status,
                        "progress": task.progress,
                        "message": task.progress_message,
                        "error_message": task.error_message,
                        "queue_position": task.queue_position,
                        "estimated_seconds": task.estimated_seconds,
                    }
                    yield {"event": "progress", "data": json.dumps(data)}

                    # 如果任务完成，发送完成事件并关闭
                    if task.status in ("completed", "failed", "cancelled"):
                        yield {"event": task.status, "data": json.dumps(data)}
                        break
                except Exception as e:
                    logger.error(f"Error fetching task progress: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "获取进度时出错"}),
                    }
                    break

                # 发送心跳包，保持连接活跃
                now = time.time()
                nonlocal last_heartbeat
                if now - last_heartbeat > heartbeat_interval:
                    yield {
                        "event": "keepalive",
                        "data": json.dumps({"timestamp": now}),
                    }
                    last_heartbeat = now

                await asyncio.sleep(2)

        except asyncio.CancelledError:
            logger.debug(f"SSE stream cancelled for task {task_id}")
        except GeneratorExit:
            logger.debug(f"SSE stream closed for task {task_id}")
        finally:
            # 确保连接被注销
            sse_manager.unregister(connection_id)

    return EventSourceResponse(event_generator())
