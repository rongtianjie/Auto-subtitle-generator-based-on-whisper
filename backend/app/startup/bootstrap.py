import hashlib
import os

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.config_service import get_config_value, set_config_value


def _compute_file_sha256(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _get_whisper_model_url(model_name: str) -> str:
    import whisper

    try:
        return whisper._MODELS[model_name]
    except KeyError as exc:
        raise ValueError(f"未知 Whisper 模型: {model_name}") from exc


def _extract_expected_sha256(model_url: str) -> str:
    expected_sha = model_url.rstrip("/").split("/")[-2]
    if len(expected_sha) != 64:
        raise ValueError(f"无法从模型地址解析 SHA256: {model_url}")
    return expected_sha


async def download_whisper_model_file(
    model_name: str,
    download_root: str,
    max_attempts: int = 5,
) -> None:
    """Download a Whisper model file with resume support and checksum validation."""
    model_url = _get_whisper_model_url(model_name)
    expected_sha = _extract_expected_sha256(model_url)
    final_path = os.path.join(download_root, f"{model_name}.pt")
    partial_path = f"{final_path}.part"

    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        head_response = await client.head(model_url)
        head_response.raise_for_status()
        total_size = int(head_response.headers.get("content-length", 0) or 0)

        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                existing_size = os.path.getsize(partial_path) if os.path.exists(partial_path) else 0
                if total_size and existing_size > total_size:
                    os.remove(partial_path)
                    existing_size = 0

                headers = {}
                write_mode = "ab" if existing_size else "wb"
                if existing_size:
                    headers["Range"] = f"bytes={existing_size}-"

                async with client.stream("GET", model_url, headers=headers) as response:
                    response.raise_for_status()
                    if existing_size and response.status_code != 206:
                        raise RuntimeError("Whisper 模型下载服务未返回可续传响应")

                    with open(partial_path, write_mode) as file_obj:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            if chunk:
                                file_obj.write(chunk)

                downloaded_size = os.path.getsize(partial_path)
                if total_size and downloaded_size != total_size:
                    raise RuntimeError(
                        f"Whisper 模型下载不完整: {downloaded_size}/{total_size}"
                    )

                actual_sha = _compute_file_sha256(partial_path)
                if actual_sha != expected_sha:
                    raise RuntimeError(
                        f"Whisper 模型 SHA256 校验失败: expected={expected_sha}, actual={actual_sha}"
                    )

                os.replace(partial_path, final_path)
                return
            except Exception as exc:
                last_error = exc
                if "SHA256" in str(exc) and os.path.exists(partial_path):
                    os.remove(partial_path)
                if attempt == max_attempts:
                    break
                logger.warning(
                    f"Whisper 模型下载失败，准备重试: {model_name} | 第 {attempt}/{max_attempts} 次 | {exc}"
                )

        raise RuntimeError(f"Whisper 模型下载失败: {model_name}") from last_error


async def ensure_whisper_model_available(model_name: str = "tiny") -> None:
    """Ensure the given Whisper model file exists locally."""
    download_root = settings.WHISPER_MODEL_DIR
    os.makedirs(download_root, exist_ok=True)

    model_path = os.path.join(download_root, f"{model_name}.pt")
    if os.path.exists(model_path):
        logger.info(f"Whisper 模型已存在，跳过下载: {model_name}")
        return

    logger.info(f"Whisper 模型缺失，开始自动下载: {model_name}")
    await download_whisper_model_file(model_name, download_root)
    logger.info(f"Whisper 模型下载完成: {model_name}")


async def fetch_available_llm_models(
    base_url: str,
    api_key: str,
    timeout: int = 10,
) -> list[str]:
    """Fetch available model IDs from an OpenAI-compatible endpoint."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=timeout) as client:
        response = await client.get("/models")
        response.raise_for_status()
        payload = response.json()

    data = payload.get("data", []) if isinstance(payload, dict) else []
    model_ids: list[str] = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            model_ids.append(str(item["id"]))
    return model_ids


async def resolve_default_llm_model(db: AsyncSession) -> str | None:
    """
    Ensure llm_model has a usable value.

    If the configured model is empty or unavailable, fall back to the first
    model reported by the configured endpoint and persist it to system config.
    """
    base_url = await get_config_value(db, "llm_base_url", settings.LLM_BASE_URL)
    api_key = await get_config_value(db, "llm_api_key", settings.LLM_API_KEY)
    timeout = int(await get_config_value(db, "llm_timeout", 15) or 15)
    configured_model = await get_config_value(db, "llm_model", None) or settings.LLM_MODEL

    model_ids = await fetch_available_llm_models(base_url, api_key, timeout)
    if not model_ids:
        logger.warning("LLM 接口未返回任何模型，保留当前 llm_model 配置")
        return configured_model or None

    if configured_model and configured_model in model_ids:
        settings.LLM_MODEL = configured_model
        return configured_model

    fallback_model = model_ids[0]
    await set_config_value(db, "llm_model", fallback_model, "LLM 模型名称")
    await db.commit()
    settings.LLM_MODEL = fallback_model

    if configured_model:
        logger.warning(
            f"当前 llm_model '{configured_model}' 不可用，已自动切换为接口返回的首个模型: {fallback_model}"
        )
    else:
        logger.info(f"llm_model 未配置，已自动选择接口返回的首个模型: {fallback_model}")

    return fallback_model
