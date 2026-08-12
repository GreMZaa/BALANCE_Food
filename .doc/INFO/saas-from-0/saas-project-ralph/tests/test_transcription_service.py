"""Tests for transcription service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.services.transcription_service import (
    DEFAULT_WHISPER_MODEL,
    SUPPORTED_FORMATS,
    SUPPORTED_LANGUAGES,
    InvalidAudioError,
    TranscriptionError,
    transcribe,
)


class TestTranscriptionServiceConstants:
    """Tests for service constants."""

    def test_supported_formats_includes_common_audio_formats(self):
        """Test that supported formats include common audio formats."""
        assert ".mp3" in SUPPORTED_FORMATS
        assert ".wav" in SUPPORTED_FORMATS
        assert ".ogg" in SUPPORTED_FORMATS
        assert ".m4a" in SUPPORTED_FORMATS

    def test_supported_languages_includes_russian_and_english(self):
        """Test that supported languages include Russian and English."""
        assert "ru" in SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES

    def test_default_whisper_model(self):
        """Test default Whisper model is set."""
        assert DEFAULT_WHISPER_MODEL == "whisper-1"


class TestTranscribeValidation:
    """Tests for input validation in transcribe function."""

    @pytest.mark.asyncio
    async def test_transcribe_file_not_found(self, tmp_path):
        """Test transcribe raises FileNotFoundError for non-existent file."""
        non_existent = tmp_path / "non_existent.mp3"

        with pytest.raises(FileNotFoundError) as exc_info:
            await transcribe(non_existent)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_unsupported_format(self, tmp_path):
        """Test transcribe raises InvalidAudioError for unsupported format."""
        # Create a file with unsupported extension
        unsupported_file = tmp_path / "audio.xyz"
        unsupported_file.write_text("test content")

        with pytest.raises(InvalidAudioError) as exc_info:
            await transcribe(unsupported_file)

        assert "Unsupported audio format" in str(exc_info.value)
        assert ".xyz" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_accepts_string_path(self, tmp_path):
        """Test transcribe accepts string path."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "transcribed text"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await transcribe(str(audio_file))
            assert result == "transcribed text"

    @pytest.mark.asyncio
    async def test_transcribe_accepts_path_object(self, tmp_path):
        """Test transcribe accepts Path object."""
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "transcribed text"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await transcribe(audio_file)
            assert result == "transcribed text"


class TestTranscribeSuccess:
    """Tests for successful transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self, tmp_path):
        """Test transcribe returns transcribed text."""
        audio_file = tmp_path / "audio.ogg"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "  Hello, world!  "
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await transcribe(audio_file)

            # Should strip whitespace
            assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_transcribe_with_language(self, tmp_path):
        """Test transcribe passes language to API."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Привет, мир!"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await transcribe(audio_file, language="ru")

            assert result == "Привет, мир!"
            # Verify language was passed
            call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
            assert call_kwargs["language"] == "ru"

    @pytest.mark.asyncio
    async def test_transcribe_without_language_auto_detects(self, tmp_path):
        """Test transcribe doesn't pass language when not specified (auto-detect)."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Some text"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await transcribe(audio_file)

            # Verify language was NOT passed
            call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
            assert "language" not in call_kwargs

    @pytest.mark.asyncio
    async def test_transcribe_with_custom_model(self, tmp_path):
        """Test transcribe passes custom model to API."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "transcribed"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await transcribe(audio_file, model="custom-whisper")

            call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
            assert call_kwargs["model"] == "custom-whisper"

    @pytest.mark.asyncio
    async def test_transcribe_uses_default_model(self, tmp_path):
        """Test transcribe uses default model when not specified."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "transcribed"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await transcribe(audio_file)

            call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
            assert call_kwargs["model"] == DEFAULT_WHISPER_MODEL


class TestTranscribeErrors:
    """Tests for error handling in transcribe function."""

    @pytest.mark.asyncio
    async def test_transcribe_api_error(self, tmp_path):
        """Test transcribe raises TranscriptionError on API error."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create = AsyncMock(
                side_effect=Exception("API connection failed")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(TranscriptionError) as exc_info:
                await transcribe(audio_file)

            assert "Failed to transcribe" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_invalid_audio_error(self, tmp_path):
        """Test transcribe raises InvalidAudioError for corrupted audio."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create = AsyncMock(
                side_effect=Exception("Could not decode audio file")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(InvalidAudioError) as exc_info:
                await transcribe(audio_file)

            assert "invalid or corrupted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_format_error_in_response(self, tmp_path):
        """Test transcribe raises InvalidAudioError for format errors in response."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create = AsyncMock(
                side_effect=Exception("Invalid audio format provided")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(InvalidAudioError):
                await transcribe(audio_file)


class TestSupportedFormats:
    """Tests for format support."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "extension",
        [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".oga"],
    )
    async def test_all_supported_formats_accepted(self, tmp_path, extension):
        """Test all supported formats are accepted."""
        audio_file = tmp_path / f"audio{extension}"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "transcribed"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            # Should not raise
            result = await transcribe(audio_file)
            assert result == "transcribed"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("extension", [".txt", ".pdf", ".exe", ".py", ".json"])
    async def test_unsupported_formats_rejected(self, tmp_path, extension):
        """Test unsupported formats are rejected."""
        audio_file = tmp_path / f"file{extension}"
        audio_file.write_bytes(b"fake content")

        with pytest.raises(InvalidAudioError):
            await transcribe(audio_file)


class TestLanguageWarning:
    """Tests for language validation warnings."""

    @pytest.mark.asyncio
    async def test_unsupported_language_logs_warning_but_proceeds(self, tmp_path, caplog):
        """Test that unsupported language logs warning but proceeds."""
        import logging

        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("bot.services.transcription_service.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "transcribed"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            with caplog.at_level(logging.WARNING):
                result = await transcribe(audio_file, language="zh")

            # Should still work
            assert result == "transcribed"

            # Should log warning
            assert any("not in supported list" in record.message for record in caplog.records)


class TestExceptionTypes:
    """Tests for exception class hierarchy."""

    def test_transcription_error_is_base_exception(self):
        """Test TranscriptionError inherits from TranscriptionServiceError."""
        from bot.services.transcription_service import (
            TranscriptionError,
            TranscriptionServiceError,
        )

        assert issubclass(TranscriptionError, TranscriptionServiceError)

    def test_invalid_audio_error_is_base_exception(self):
        """Test InvalidAudioError inherits from TranscriptionServiceError."""
        from bot.services.transcription_service import (
            InvalidAudioError,
            TranscriptionServiceError,
        )

        assert issubclass(InvalidAudioError, TranscriptionServiceError)

    def test_base_exception_is_exception(self):
        """Test TranscriptionServiceError inherits from Exception."""
        from bot.services.transcription_service import TranscriptionServiceError

        assert issubclass(TranscriptionServiceError, Exception)
