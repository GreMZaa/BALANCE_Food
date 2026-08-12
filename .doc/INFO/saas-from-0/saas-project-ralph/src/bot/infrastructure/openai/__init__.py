"""OpenAI infrastructure - API client."""

from bot.infrastructure.openai.client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL,
    DEFAULT_RETRY_DELAY,
    DEFAULT_RETRY_MULTIPLIER,
    DEFAULT_TIMEOUT,
    OpenAIClientError,
    OpenAIConnectionError,
    OpenAIRateLimitError,
    OpenAITimeoutError,
    chat_completion_with_retry,
    close_openai_client,
    get_openai_client,
    init_openai_client,
)

__all__ = [
    # Functions
    "init_openai_client",
    "get_openai_client",
    "close_openai_client",
    "chat_completion_with_retry",
    # Exceptions
    "OpenAIClientError",
    "OpenAIConnectionError",
    "OpenAIRateLimitError",
    "OpenAITimeoutError",
    # Constants
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_RETRY_MULTIPLIER",
    "DEFAULT_MODEL",
]
