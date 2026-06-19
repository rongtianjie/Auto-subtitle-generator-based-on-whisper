import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, Float, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'upload' | 'url'
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Whisper 配置
    whisper_model: Mapped[str] = mapped_column(String(20), nullable=False, default="base")

    # 翻译 LLM 配置
    translate_llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 输出配置
    output_formats: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)  # ["txt", "srt", "bilingual_srt"]
    translate_target_langs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # ["zh", "ja", ...]

    # 状态与进度
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending / queued / processing / completed / failed / cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    progress_message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 队列信息
    queue_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 错误信息
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 取消请求标记
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 游客 IP（已登录用户为 None）
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # 时间戳
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="tasks")
    outputs = relationship("TaskOutput", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        # 队列查询优化：status + queue_position 复合索引（快速查找待处理任务）
        Index("idx_tasks_status_position", "status", "queue_position"),
        # 用户任务列表查询优化：user_id + created_at
        Index("idx_tasks_user_created", "user_id", "created_at"),
        # 创建时间索引（用于按时间排序和过期清理）
        Index("idx_tasks_created_at", "created_at"),
        # 游客任务统计优化：client_ip + created_at（用于游客日限制检查）
        Index("idx_tasks_client_ip_created", "client_ip", "created_at"),
        # 任务完成时间查询优化（用于分析和报表）
        Index("idx_tasks_completed_at", "completed_at"),
        # 状态 + created_at 复合索引（用于按状态过滤列表）
        Index("idx_tasks_status_created", "status", "created_at"),
    )
