"""OpenAI API client with async support, retry logic and error handling."""

import asyncio
import logging
from typing import Any

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError

from bot.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIClientError(Exception):
    """Base exception for OpenAI client errors."""

    pass


class OpenAIConnectionError(OpenAIClientError):
    """Raised when connection to OpenAI API fails."""

    pass


class OpenAIRateLimitError(OpenAIClientError):
    """Raised when rate limit is exceeded."""

    pass


class OpenAITimeoutError(OpenAIClientError):
    """Raised when request times out."""

    pass


# Singleton client instance
_client: AsyncOpenAI | None = None

# Default configuration
DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_RETRY_MULTIPLIER = 2.0
DEFAULT_MODEL = "gpt-4o-mini"


def init_openai_client(
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = 0,  # We handle retries manually for more control
) -> AsyncOpenAI:
    """Initialize the OpenAI async client.

    Args:
        timeout: Request timeout in seconds
        max_retries: Number of retries for failed requests (handled by httpx)

    Returns:
        Initialized AsyncOpenAI client
    """
    global _client

    if _client is not None:
        logger.debug("OpenAI client already initialized, returning existing instance")
        return _client

    api_key = settings.openai_api_key.get_secret_value()

    _client = AsyncOpenAI(
        api_key=api_key,
        timeout=timeout,
        max_retries=max_retries,
    )

    logger.info("OpenAI client initialized successfully")
    return _client


def get_openai_client() -> AsyncOpenAI:
    """Get the initialized OpenAI client.

    Returns:
        AsyncOpenAI client instance

    Raises:
        OpenAIClientError: If client is not initialized
    """
    if _client is None:
        raise OpenAIClientError(
            "OpenAI client not initialized. Call init_openai_client() first."
        )
    return _client


async def close_openai_client() -> None:
    """Close the OpenAI client and release resources."""
    global _client

    if _client is not None:
        await _client.close()
        _client = None
        logger.info("OpenAI client closed")


async def chat_completion_with_retry(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    retry_multiplier: float = DEFAULT_RETRY_MULTIPLIER,
    timeout: float | None = None,
    **kwargs: Any,
) -> str:
    """Make a chat completion request with exponential backoff retry.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: OpenAI model to use
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens in response
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        retry_multiplier: Multiplier for exponential backoff
        timeout: Request timeout override (uses client default if None)
        **kwargs: Additional arguments passed to OpenAI API

    Returns:
        The content of the assistant's response

    Raises:
        OpenAIClientError: For client initialization errors
        OpenAIConnectionError: For connection failures after all retries
        OpenAIRateLimitError: For rate limit errors after all retries
        OpenAITimeoutError: For timeout errors after all retries
    """
    client = get_openai_client()
    current_delay = retry_delay
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.debug(
                f"Making chat completion request (attempt {attempt + 1}/{max_retries + 1})"
            )

            request_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs,
            }

            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens

            if timeout is not None:
                request_kwargs["timeout"] = timeout

            response = await client.chat.completions.create(**request_kwargs)

            content = response.choices[0].message.content
            if content is None:
                content = ""

            logger.debug(f"Chat completion successful, received {len(content)} chars")
            return content

        except TimeoutError as e:
            last_exception = e
            logger.warning(f"Request timed out (attempt {attempt + 1}/{max_retries + 1})")

            if attempt < max_retries:
                logger.info(f"Retrying in {current_delay:.1f}s...")
                await asyncio.sleep(current_delay)
                current_delay *= retry_multiplier
            else:
                raise OpenAITimeoutError(
                    f"Request timed out after {max_retries + 1} attempts"
                ) from e

        except RateLimitError as e:
            last_exception = e
            logger.warning(
                f"Rate limit exceeded (attempt {attempt + 1}/{max_retries + 1}): {e}"
            )

            if attempt < max_retries:
                # Use longer delay for rate limits
                rate_limit_delay = current_delay * 2
                logger.info(f"Retrying in {rate_limit_delay:.1f}s due to rate limit...")
                await asyncio.sleep(rate_limit_delay)
                current_delay *= retry_multiplier
            else:
                raise OpenAIRateLimitError(
                    f"Rate limit exceeded after {max_retries + 1} attempts"
                ) from e

        except APIConnectionError as e:
            last_exception = e
            logger.warning(
                f"Connection error (attempt {attempt + 1}/{max_retries + 1}): {e}"
            )

            if attempt < max_retries:
                logger.info(f"Retrying in {current_delay:.1f}s...")
                await asyncio.sleep(current_delay)
                current_delay *= retry_multiplier
            else:
                raise OpenAIConnectionError(
                    f"Connection failed after {max_retries + 1} attempts: {e}"
                ) from e

        except APIStatusError as e:
            # Don't retry on client errors (4xx except 429)
            if 400 <= e.status_code < 500 and e.status_code != 429:
                logger.error(f"API error (non-retryable): {e.status_code} - {e.message}")
                raise OpenAIClientError(f"API error: {e.message}") from e

            last_exception = e
            logger.warning(
                f"API error (attempt {attempt + 1}/{max_retries + 1}): "
                f"{e.status_code} - {e.message}"
            )

            if attempt < max_retries:
                logger.info(f"Retrying in {current_delay:.1f}s...")
                await asyncio.sleep(current_delay)
                current_delay *= retry_multiplier
            else:
                raise OpenAIConnectionError(
                    f"API error after {max_retries + 1} attempts: {e.message}"
                ) from e

    # This should never be reached, but just in case
    if last_exception:
        raise OpenAIClientError(f"Unexpected error: {last_exception}") from last_exception
    raise OpenAIClientError("Unexpected error in retry loop")
