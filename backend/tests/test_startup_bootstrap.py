from unittest.mock import AsyncMock

import pytest

from app.startup import bootstrap


class TestEnsureWhisperModelAvailable:
    @pytest.mark.asyncio
    async def test_skip_download_when_model_exists(self, tmp_path, monkeypatch):
        model_path = tmp_path / "tiny.pt"
        model_path.write_bytes(b"ready")

        monkeypatch.setattr(bootstrap.settings, "WHISPER_MODEL_DIR", str(tmp_path))
        mock_download = AsyncMock()
        monkeypatch.setattr(bootstrap, "download_whisper_model_file", mock_download)

        await bootstrap.ensure_whisper_model_available("tiny")

        mock_download.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_download_model_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bootstrap.settings, "WHISPER_MODEL_DIR", str(tmp_path))
        mock_download = AsyncMock()
        monkeypatch.setattr(bootstrap, "download_whisper_model_file", mock_download)

        await bootstrap.ensure_whisper_model_available("tiny")

        mock_download.assert_awaited_once_with("tiny", str(tmp_path))

    @pytest.mark.asyncio
    async def test_propagate_download_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bootstrap.settings, "WHISPER_MODEL_DIR", str(tmp_path))
        mock_download = AsyncMock(side_effect=RuntimeError("network failure"))
        monkeypatch.setattr(bootstrap, "download_whisper_model_file", mock_download)

        with pytest.raises(RuntimeError, match="network failure"):
            await bootstrap.ensure_whisper_model_available("tiny")


class TestDownloadWhisperModelFile:
    @pytest.mark.asyncio
    async def test_extract_expected_sha256_from_url(self):
        model_url = (
            "https://example.invalid/models/"
            "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"
        )

        assert (
            bootstrap._extract_expected_sha256(model_url)
            == "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9"
        )


class TestResolveDefaultLlmModel:
    @pytest.mark.asyncio
    async def test_keep_existing_model_when_available(self, monkeypatch):
        db = AsyncMock()
        monkeypatch.setattr(
            bootstrap,
            "get_config_value",
            AsyncMock(side_effect=[
                "http://llm.example/v1",
                "key-123",
                15,
                "model-b",
            ]),
        )
        monkeypatch.setattr(
            bootstrap,
            "fetch_available_llm_models",
            AsyncMock(return_value=["model-a", "model-b"]),
        )
        mock_set = AsyncMock()
        monkeypatch.setattr(bootstrap, "set_config_value", mock_set)
        monkeypatch.setattr(bootstrap.settings, "LLM_MODEL", "")

        selected = await bootstrap.resolve_default_llm_model(db)

        assert selected == "model-b"
        assert bootstrap.settings.LLM_MODEL == "model-b"
        mock_set.assert_not_awaited()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pick_first_model_when_current_is_empty(self, monkeypatch):
        db = AsyncMock()
        monkeypatch.setattr(
            bootstrap,
            "get_config_value",
            AsyncMock(side_effect=[
                "http://llm.example/v1",
                "key-123",
                15,
                "",
            ]),
        )
        monkeypatch.setattr(
            bootstrap,
            "fetch_available_llm_models",
            AsyncMock(return_value=["model-a", "model-b"]),
        )
        mock_set = AsyncMock()
        monkeypatch.setattr(bootstrap, "set_config_value", mock_set)
        monkeypatch.setattr(bootstrap.settings, "LLM_MODEL", "")

        selected = await bootstrap.resolve_default_llm_model(db)

        assert selected == "model-a"
        assert bootstrap.settings.LLM_MODEL == "model-a"
        mock_set.assert_awaited_once_with(db, "llm_model", "model-a", "LLM 模型名称")
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pick_first_model_when_current_is_invalid(self, monkeypatch):
        db = AsyncMock()
        monkeypatch.setattr(
            bootstrap,
            "get_config_value",
            AsyncMock(side_effect=[
                "http://llm.example/v1",
                "key-123",
                15,
                "missing-model",
            ]),
        )
        monkeypatch.setattr(
            bootstrap,
            "fetch_available_llm_models",
            AsyncMock(return_value=["model-a", "model-b"]),
        )
        mock_set = AsyncMock()
        monkeypatch.setattr(bootstrap, "set_config_value", mock_set)
        monkeypatch.setattr(bootstrap.settings, "LLM_MODEL", "missing-model")

        selected = await bootstrap.resolve_default_llm_model(db)

        assert selected == "model-a"
        assert bootstrap.settings.LLM_MODEL == "model-a"
        mock_set.assert_awaited_once_with(db, "llm_model", "model-a", "LLM 模型名称")
        db.commit.assert_awaited_once()
