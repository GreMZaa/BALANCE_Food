"""Tests for OpenAI client module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIConnectionError, APIStatusError, RateLimitError

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


@pytest.fixture(autouse=True)
async def reset_client():
    """Reset the global client before each test."""
    import bot.infrastructure.openai.client as client_module

    client_module._client = None
    yield
    client_module._client = None


class TestOpenAIClientInitialization:
    """Tests for client initialization and singleton pattern."""

    def test_get_client_not_initialized_raises_error(self):
        """Test that getting client before initialization raises error."""
        with pytest.raises(OpenAIClientError) as exc_info:
            get_openai_client()

        assert "not initialized" in str(exc_info.value)

    def test_init_openai_client_creates_client(self):
        """Test that init_openai_client creates an async client."""
        client = init_openai_client()
        assert client is not None

        # Second call should return the same client (singleton)
        client2 = init_openai_client()
        assert client is client2

    def test_get_openai_client_after_init(self):
        """Test that get_openai_client works after initialization."""
        init_openai_client()
        client = get_openai_client()
        assert client is not None

    async def test_close_openai_client(self):
        """Test that close_openai_client clears the client."""
        import bot.infrastructure.openai.client as client_module

        init_openai_client()
        assert client_module._client is not None

        await close_openai_client()
        assert client_module._client is None

    async def test_close_openai_client_when_not_initialized(self):
        """Test that close_openai_client is safe when client not initialized."""
        # Should not raise any error
        await close_openai_client()

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = init_openai_client(timeout=60.0)
        assert client is not None
        # Timeout is passed directly to httpx, verify it was set
        assert client.timeout == 60.0


class TestOpenAIClientExceptions:
    """Tests for exception classes."""

    def test_openai_client_error_inherits_from_exception(self):
        """Test that OpenAIClientError is a proper exception."""
        error = OpenAIClientError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_openai_connection_error_inherits_from_client_error(self):
        """Test that OpenAIConnectionError inherits from OpenAIClientError."""
        error = OpenAIConnectionError("connection failed")
        assert isinstance(error, OpenAIClientError)
        assert str(error) == "connection failed"

    def test_openai_rate_limit_error_inherits_from_client_error(self):
        """Test that OpenAIRateLimitError inherits from OpenAIClientError."""
        error = OpenAIRateLimitError("rate limited")
        assert isinstance(error, OpenAIClientError)
        assert str(error) == "rate limited"

    def test_openai_timeout_error_inherits_from_client_error(self):
        """Test that OpenAITimeoutError inherits from OpenAIClientError."""
        error = OpenAITimeoutError("timed out")
        assert isinstance(error, OpenAIClientError)
        assert str(error) == "timed out"


class TestChatCompletionWithRetry:
    """Tests for chat completion with retry logic."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        init_openai_client()
        return get_openai_client()

    @pytest.fixture
    def sample_messages(self):
        """Sample messages for chat completion."""
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

    async def test_successful_completion(self, mock_client, sample_messages):
        """Test successful chat completion."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello! How can I help you?"

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await chat_completion_with_retry(sample_messages)

            assert result == "Hello! How can I help you?"
            mock_create.assert_called_once()

    async def test_completion_with_custom_model(self, mock_client, sample_messages):
        """Test chat completion with custom model."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await chat_completion_with_retry(sample_messages, model="gpt-4o")

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "gpt-4o"

    async def test_completion_with_max_tokens(self, mock_client, sample_messages):
        """Test chat completion with max_tokens."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await chat_completion_with_retry(sample_messages, max_tokens=100)

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["max_tokens"] == 100

    async def test_retry_on_connection_error(self, mock_client, sample_messages):
        """Test retry on connection error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # First call fails, second succeeds
            mock_create.side_effect = [
                APIConnectionError(request=MagicMock()),
                mock_response,
            ]

            result = await chat_completion_with_retry(
                sample_messages,
                max_retries=1,
                retry_delay=0.01,  # Fast for tests
            )

            assert result == "Success after retry"
            assert mock_create.call_count == 2

    async def test_connection_error_exhausts_retries(self, mock_client, sample_messages):
        """Test that connection error is raised after all retries exhausted."""
        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = APIConnectionError(request=MagicMock())

            with pytest.raises(OpenAIConnectionError) as exc_info:
                await chat_completion_with_retry(
                    sample_messages,
                    max_retries=2,
                    retry_delay=0.01,
                )

            assert "3 attempts" in str(exc_info.value)  # 1 initial + 2 retries
            assert mock_create.call_count == 3

    async def test_retry_on_rate_limit(self, mock_client, sample_messages):
        """Test retry on rate limit error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success"

        mock_rate_limit = MagicMock(spec=RateLimitError)
        mock_rate_limit.status_code = 429
        mock_rate_limit.message = "Rate limited"

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [
                RateLimitError(
                    message="Rate limited",
                    response=MagicMock(status_code=429),
                    body=None,
                ),
                mock_response,
            ]

            result = await chat_completion_with_retry(
                sample_messages,
                max_retries=1,
                retry_delay=0.01,
            )

            assert result == "Success"
            assert mock_create.call_count == 2

    async def test_rate_limit_exhausts_retries(self, mock_client, sample_messages):
        """Test that rate limit error is raised after all retries exhausted."""
        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )

            with pytest.raises(OpenAIRateLimitError) as exc_info:
                await chat_completion_with_retry(
                    sample_messages,
                    max_retries=1,
                    retry_delay=0.01,
                )

            assert "Rate limit exceeded" in str(exc_info.value)

    async def test_retry_on_timeout(self, mock_client, sample_messages):
        """Test retry on timeout error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success"

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [
                TimeoutError(),
                mock_response,
            ]

            result = await chat_completion_with_retry(
                sample_messages,
                max_retries=1,
                retry_delay=0.01,
            )

            assert result == "Success"
            assert mock_create.call_count == 2

    async def test_timeout_exhausts_retries(self, mock_client, sample_messages):
        """Test that timeout error is raised after all retries exhausted."""
        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = TimeoutError()

            with pytest.raises(OpenAITimeoutError) as exc_info:
                await chat_completion_with_retry(
                    sample_messages,
                    max_retries=1,
                    retry_delay=0.01,
                )

            assert "timed out" in str(exc_info.value)

    async def test_no_retry_on_client_error_4xx(self, mock_client, sample_messages):
        """Test that 4xx errors (except 429) are not retried."""
        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = APIStatusError(
                message="Bad request",
                response=mock_response,
                body=None,
            )

            with pytest.raises(OpenAIClientError) as exc_info:
                await chat_completion_with_retry(
                    sample_messages,
                    max_retries=2,
                    retry_delay=0.01,
                )

            assert "Bad request" in str(exc_info.value)
            assert mock_create.call_count == 1  # No retries

    async def test_retry_on_server_error_5xx(self, mock_client, sample_messages):
        """Test that 5xx errors are retried."""
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success"

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [
                APIStatusError(
                    message="Internal server error",
                    response=mock_response_error,
                    body=None,
                ),
                mock_response,
            ]

            result = await chat_completion_with_retry(
                sample_messages,
                max_retries=1,
                retry_delay=0.01,
            )

            assert result == "Success"
            assert mock_create.call_count == 2

    async def test_completion_without_init_raises_error(self, sample_messages):
        """Test that completion without client init raises error."""
        import bot.infrastructure.openai.client as client_module

        client_module._client = None

        with pytest.raises(OpenAIClientError) as exc_info:
            await chat_completion_with_retry(sample_messages)

        assert "not initialized" in str(exc_info.value)

    async def test_empty_content_returns_empty_string(self, mock_client, sample_messages):
        """Test that None content is converted to empty string."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        with patch.object(
            mock_client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await chat_completion_with_retry(sample_messages)

            assert result == ""


class TestDefaultConstants:
    """Tests for default constants."""

    def test_default_timeout(self):
        """Test default timeout value."""
        assert DEFAULT_TIMEOUT == 30.0

    def test_default_max_retries(self):
        """Test default max retries value."""
        assert DEFAULT_MAX_RETRIES == 3

    def test_default_retry_delay(self):
        """Test default retry delay value."""
        assert DEFAULT_RETRY_DELAY == 1.0

    def test_default_retry_multiplier(self):
        """Test default retry multiplier value."""
        assert DEFAULT_RETRY_MULTIPLIER == 2.0

    def test_default_model(self):
        """Test default model value."""
        assert DEFAULT_MODEL == "gpt-4o-mini"
