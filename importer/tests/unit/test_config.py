"""Unit tests for configuration module."""

import pytest
import os
from pathlib import Path

from config import BibleImporterSettings


class TestBibleImporterSettings:
    """Test configuration settings."""

    def test_default_settings(self):
        """Verify default configuration values."""
        settings = BibleImporterSettings()

        assert settings.prism_base_url == "http://localhost:8100"
        assert settings.prism_timeout == 300
        assert settings.target_chunk_tokens == 350
        assert settings.min_chunk_tokens == 50
        assert settings.max_chunk_tokens == 500
        assert settings.batch_size == 100
        assert settings.embed is True
        assert settings.data_dir == Path("/dpool/aiml-stack/data/bible")

    def test_env_override_prism_url(self, monkeypatch):
        """BIBLE_IMPORTER_PRISM_BASE_URL overrides default."""
        monkeypatch.setenv("BIBLE_IMPORTER_PRISM_BASE_URL", "http://custom:9999")

        settings = BibleImporterSettings()

        assert settings.prism_base_url == "http://custom:9999"

    def test_env_override_chunk_tokens(self, monkeypatch):
        """BIBLE_IMPORTER_TARGET_CHUNK_TOKENS overrides default."""
        monkeypatch.setenv("BIBLE_IMPORTER_TARGET_CHUNK_TOKENS", "500")

        settings = BibleImporterSettings()

        assert settings.target_chunk_tokens == 500

    def test_env_override_batch_size(self, monkeypatch):
        """BIBLE_IMPORTER_BATCH_SIZE overrides default."""
        monkeypatch.setenv("BIBLE_IMPORTER_BATCH_SIZE", "50")

        settings = BibleImporterSettings()

        assert settings.batch_size == 50

    def test_env_override_embed(self, monkeypatch):
        """BIBLE_IMPORTER_EMBED overrides default."""
        monkeypatch.setenv("BIBLE_IMPORTER_EMBED", "false")

        settings = BibleImporterSettings()

        assert settings.embed is False

    def test_env_case_insensitive(self, monkeypatch):
        """Environment variables are case-insensitive."""
        monkeypatch.setenv("bible_importer_batch_size", "75")

        settings = BibleImporterSettings()

        assert settings.batch_size == 75

    def test_data_dir_is_path(self):
        """data_dir should be a Path object."""
        settings = BibleImporterSettings()

        assert isinstance(settings.data_dir, Path)

    def test_token_limits_relationship(self):
        """Token limits should have logical relationship."""
        settings = BibleImporterSettings()

        assert settings.min_chunk_tokens < settings.target_chunk_tokens
        assert settings.target_chunk_tokens < settings.max_chunk_tokens

    def test_timeout_positive(self):
        """Timeout should be positive integer."""
        settings = BibleImporterSettings()

        assert settings.prism_timeout > 0
        assert isinstance(settings.prism_timeout, int)
