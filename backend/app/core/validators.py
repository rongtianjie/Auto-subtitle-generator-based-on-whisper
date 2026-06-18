"""
文件上传验证器

包含:
- MIME 类型验证
- 文件格式检测
- 文件名清理（防止 path traversal）
- 恶意文件扫描集成点
"""

from pathlib import Path
from typing import Optional
import mimetypes

from app.core.exceptions import InvalidFileTypeException


# 允许的 MIME 类型
ALLOWED_AUDIO_MIMES = {
    "audio/mpeg",           # .mp3
    "audio/mp4",            # .m4a
    "audio/wav",            # .wav
    "audio/webm",           # .webm
    "audio/ogg",            # .ogg
    "audio/flac",           # .flac
    "audio/aac",            # .aac
    "audio/x-m4a",          # .m4a (alternative)
    "audio/x-wav",          # .wav (alternative)
    "audio/x-flac",         # .flac (alternative)
}

ALLOWED_VIDEO_MIMES = {
    "video/mp4",            # .mp4
    "video/mpeg",           # .mpeg, .mpg
    "video/webm",           # .webm
    "video/quicktime",      # .mov
    "video/x-msvideo",      # .avi
    "video/x-matroska",     # .mkv
    "video/x-flv",          # .flv
    "video/3gpp",           # .3gp
    "video/3gpp2",          # .3g2
    "application/x-mpegURL", # .m3u8 (stream)
}

ALLOWED_MIMES = ALLOWED_AUDIO_MIMES | ALLOWED_VIDEO_MIMES


def clean_filename(filename: str) -> str:
    """
    清理文件名，防止 path traversal 攻击

    例如: "../../../etc/passwd" -> "etc_passwd"
    """
    if not filename:
        raise InvalidFileTypeException("文件名不能为空")

    # 使用 Path 确保只获取文件名，移除任何路径组件
    cleaned = Path(filename).name

    if not cleaned:
        raise InvalidFileTypeException("无效的文件名")

    return cleaned


def validate_mime_type(filename: str, content_type: Optional[str] = None) -> str:
    """
    验证 MIME 类型

    Args:
        filename: 文件名
        content_type: 上传时的 Content-Type 头

    Returns:
        验证后的 MIME 类型

    Raises:
        InvalidFileTypeException: 如果 MIME 类型不支持
    """
    # 尝试从 Content-Type 头获取
    if content_type and content_type in ALLOWED_MIMES:
        return content_type

    # 从文件扩展名猜测
    guessed_type, _ = mimetypes.guess_type(filename)

    if guessed_type and guessed_type in ALLOWED_MIMES:
        return guessed_type

    # 如果都没有找到有效的 MIME 类型，拒绝
    raise InvalidFileTypeException(
        "文件类型不支持，仅支持常见的音频和视频格式 (mp3, mp4, wav, webm, mkv, mov 等)"
    )


def detect_file_type_by_magic(file_path: str) -> Optional[str]:
    """
    使用 magic 字节检测文件类型

    这是一个增强的文件类型检测，不依赖扩展名或 Content-Type

    Args:
        file_path: 文件路径

    Returns:
        检测到的 MIME 类型，如果无法识别则返回 None
    """
    try:
        import magic

        mime = magic.Magic(mime=True)
        detected_type = mime.from_file(file_path)
        return detected_type
    except ImportError:
        # 如果未安装 python-magic，跳过此检测
        return None
    except Exception:
        # 其他错误也忽略，文件可能损坏
        return None


def scan_malware(file_path: str) -> bool:
    """
    扫描文件是否包含恶意代码

    这是一个集成点，可以接入 ClamAV 或其他反病毒引擎

    Args:
        file_path: 文件路径

    Returns:
        True: 文件安全, False: 文件可能包含恶意代码
    """
    # TODO: 集成反病毒引擎 (例如 ClamAV)
    # 当前版本跳过此检测
    return True


def validate_upload(filename: str, content_type: Optional[str] = None) -> str:
    """
    完整的文件上传验证流程

    Args:
        filename: 原始文件名
        content_type: Content-Type 头

    Returns:
        清理后的文件名

    Raises:
        InvalidFileTypeException: 如果验证失败
    """
    # 1. 清理文件名
    cleaned = clean_filename(filename)

    # 2. 验证 MIME 类型
    validate_mime_type(cleaned, content_type)

    return cleaned
