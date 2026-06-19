from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from uuid import UUID


class TaskCreateRequest(BaseModel):
    """创建任务请求 schema (表单提交)"""

    source_type: str = Field(..., pattern="^(upload|url)$", description="数据来源: upload 或 url")
    source_url: Optional[str] = Field(None, description="视频 URL (source_type=url 时必需)")
    title: Optional[str] = Field(None, max_length=255, description="任务标题")
    whisper_model: str = Field(
        "base",
        pattern="^(tiny|base|small|medium|large)$",
        description="Whisper 模型"
    )
    output_formats: List[str] = Field(
        ["txt", "srt", "bilingual_srt"],
        description="输出格式列表"
    )
    translate_target_langs: Optional[List[str]] = Field(
        None,
        description="翻译目标语言列表"
    )

    @field_validator("output_formats")
    @classmethod
    def validate_output_formats(cls, v):
        """验证输出格式"""
        if not v:
            raise ValueError("至少需要选择一个输出格式")

        allowed = {"txt", "srt", "bilingual_srt", "vtt"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"不支持的输出格式: {invalid}")

        return v

    @field_validator("translate_target_langs", mode="before")
    @classmethod
    def validate_languages(cls, v):
        """验证翻译语言"""
        if not v:
            return None

        # 这里可以配置支持的语言列表
        supported = {
            "zh", "en", "ja", "ko", "fr", "de", "es", "ru", "pt", "ar", "th", "vi",
            "it", "nl", "pl", "tr", "id"
        }
        invalid = set(v) - supported
        if invalid:
            raise ValueError(f"不支持的语言代码: {invalid}")

        return v

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v, info):
        """验证 source_url (当 source_type=url 时)"""
        values = getattr(info, "data", {}) or {}
        if values.get("source_type") == "url" and not v:
            raise ValueError("source_type=url 时必须提供 source_url")
        return v


class TaskCreate(BaseModel):
    """创建任务请求（通过 URL 提交时）"""
    source_type: str = Field(..., pattern="^(upload|url)$")
    source_url: Optional[str] = None
    title: Optional[str] = None
    whisper_model: str = Field(default="base", pattern="^(tiny|base|small|medium|large)$")
    output_formats: List[str] = Field(default=["txt", "srt", "bilingual_srt"])
    translate_target_langs: Optional[List[str]] = None


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""

    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, pattern="^(pending|queued|processing|completed|failed|cancelled)$")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    progress_message: Optional[str] = Field(None, max_length=255)


class TaskResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: str
    source_type: str
    source_url: Optional[str] = None
    source_filename: Optional[str] = None
    whisper_model: str
    output_formats: List[str]
    translate_target_langs: Optional[List[str]] = None
    status: str
    progress: float
    progress_message: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_seconds: Optional[int] = None
    error_message: Optional[str] = None
    cancel_requested: bool = False
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TaskOutputResponse(BaseModel):
    id: str
    task_id: str
    format_type: str
    language_pair: Optional[str] = None
    file_path: str
    file_size: Optional[int] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class QueueStatusResponse(BaseModel):
    pending_count: int
    processing_count: int
    avg_duration: int
