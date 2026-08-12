"""Audio transcription service using OpenAI Whisper API."""

import logging
from pathlib import Path

from bot.infrastructure.openai.client import get_openai_client

logger = logging.getLogger(__name__)


class TranscriptionServiceError(Exception):
    """Base exception for transcription service errors."""

    pass


class TranscriptionError(TranscriptionServiceError):
    """Raised when audio transcription fails."""

    pass


class InvalidAudioError(TranscriptionServiceError):
    """Raised when audio file is invalid or corrupted."""

    pass


# Supported audio formats by Whisper API
SUPPORTED_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".oga"}

# Supported languages for transcription
SUPPORTED_LANGUAGES = {"ru", "en"}

# Default model
DEFAULT_WHISPER_MODEL = "whisper-1"


async def transcribe(
    audio_file: Path | str,
    language: str | None = None,
    model: str = DEFAULT_WHISPER_MODEL,
) -> str:
    """Transcribe an audio file to text using OpenAI Whisper API.

    Args:
        audio_file: Path to the audio file
        language: Language code (e.g., 'ru', 'en'). If None, auto-detects.
        model: Whisper model to use

    Returns:
        Transcribed text

    Raises:
        TranscriptionError: If transcription fails
        InvalidAudioError: If audio file is invalid
        FileNotFoundError: If audio file doesn't exist
    """
    audio_path = Path(audio_file) if isinstance(audio_file, str) else audio_file

    # Validate file exists
    if not audio_path.exists():
        logger.error(f"Audio file not found: {audio_path}")
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Validate file format
    suffix = audio_path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported audio format: {suffix}")
        raise InvalidAudioError(
            f"Unsupported audio format: {suffix}. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    # Validate language if provided
    if language is not None and language not in SUPPORTED_LANGUAGES:
        logger.warning(
            f"Language '{language}' not in supported list {SUPPORTED_LANGUAGES}, "
            "proceeding anyway as Whisper may support it"
        )

    logger.info(
        f"Transcribing audio: file={audio_path.name}, "
        f"size={audio_path.stat().st_size} bytes, language={language or 'auto'}"
    )

    try:
        client = get_openai_client()

        with open(audio_path, "rb") as audio:
            kwargs: dict = {
                "model": model,
                "file": audio,
            }

            # Only add language if specified (auto-detect otherwise)
            if language:
                kwargs["language"] = language

            response = await client.audio.transcriptions.create(**kwargs)

        text = response.text.strip()
        logger.info(f"Transcription successful: {len(text)} characters")
        return text

    except FileNotFoundError:
        raise
    except InvalidAudioError:
        raise
    except Exception as e:
        error_message = str(e).lower()

        # Check for common audio-related errors
        if "audio" in error_message or "format" in error_message or "decode" in error_message:
            logger.error(f"Invalid or corrupted audio file: {e}")
            raise InvalidAudioError(f"Audio file is invalid or corrupted: {e}") from e

        logger.error(f"Transcription failed: {e}")
        raise TranscriptionError(f"Failed to transcribe audio: {e}") from e
