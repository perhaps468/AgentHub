import os
from unittest.mock import patch

import pytest

from app.core.config import Settings, get_settings


class TestSettingsDefaults:
    def test_qwen_model_defaults_to_qwen_plus(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("app.core.config.load_env_file"),
        ):
            settings = get_settings()
            assert settings.qwen_model == "qwen-plus"

    def test_qwen_base_url_has_default(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("app.core.config.load_env_file"),
        ):
            settings = get_settings()
            assert settings.qwen_base_url is not None
            assert "dashscope" in settings.qwen_base_url


class TestSettingsEnvOverrides:
    def test_qwen_api_key_reads_from_env(self):
        with (
            patch.dict(os.environ, {"QWEN_API_KEY": "test-key-123"}, clear=True),
            patch("app.core.config.load_env_file"),
        ):
            settings = get_settings()
            assert settings.qwen_api_key == "test-key-123"

    def test_qwen_api_key_is_optional(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("app.core.config.load_env_file"),
        ):
            settings = get_settings()
            assert settings.qwen_api_key is None

    def test_qwen_model_overridable(self):
        with (
            patch.dict(os.environ, {"QWEN_MODEL": "qwen-max"}, clear=True),
            patch("app.core.config.load_env_file"),
        ):
            settings = get_settings()
            assert settings.qwen_model == "qwen-max"

    def test_qwen_base_url_overridable(self):
        with (
            patch.dict(os.environ, {"QWEN_BASE_URL": "https://custom.example.com/v1"}, clear=True),
            patch("app.core.config.load_env_file"),
        ):
            settings = get_settings()
            assert settings.qwen_base_url == "https://custom.example.com/v1"
