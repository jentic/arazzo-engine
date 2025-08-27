import os
from unittest.mock import patch

from arazzo_generator.llm.litellm_service import LiteLLMService


class TestLLMServiceInitialization:
    # Tests default initialisation of LLM service with Gemini provider for specific default config model
    def test_default_init_default_model(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"
        assert svc.llm_model == "gemini/gemini-2.0-flash"

    # Tests initialisation of LLM service with Anthropic provider for any model
    def test_anthropic_init_any_model(self):
        svc = LiteLLMService(
            api_key="test-key",
            llm_provider="anthropic",
            llm_model="claude-3-sonnet-20240229",
        )
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "anthropic"
        assert svc.llm_model == "claude-3-sonnet-20240229"

    # Tests initialisation of LLM service with OpenAI provider for any model
    def test_openai_init_any_model(self):
        svc = LiteLLMService(api_key="test-key", llm_provider="openai", llm_model="gpt-4o")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "openai"
        assert svc.llm_model == "gpt-4o"

    # Tests initialisation of LLM service with Gemini provider for any model
    def test_gemini_init_any_model(self):
        svc = LiteLLMService(
            api_key="test-key",
            llm_provider="gemini",
            llm_model="gemini/gemini-2.0-flash",
        )
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"
        assert svc.llm_model == "gemini/gemini-2.0-flash"

    # Tests invalid provider (should not raise exception, just use fallback)
    def test_invalid_provider(self):
        svc = LiteLLMService(api_key="test-key", llm_provider="invalid", llm_model="invalid-model")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "invalid"
        assert svc.llm_model == "invalid-model"

    # Tests that appropriate warning is logged when no API key is provided
    def test_init_logs_warning_no_api_key(self, caplog):
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing log records
            caplog.clear()

            # Initialize the service
            LiteLLMService(api_key=None)

            # Check that the warning was logged
            assert "No API key provided for gemini LLM service" in caplog.text

    # Tests is_available with API key
    def test_is_available_with_api_key(self, monkeypatch):
        # Mock the completion call to return a successful response
        def mock_completion(*args, **kwargs):
            return {"choices": [{"message": {"content": "test"}}]}

        monkeypatch.setattr("litellm.completion", mock_completion)
        svc = LiteLLMService(api_key="test-key")
        assert svc.is_available() is True

    # Tests is_available without API key
    def test_is_available_without_api_key(self, monkeypatch):
        # Mock the completion call to raise an authentication error
        def mock_completion(*args, **kwargs):
            raise Exception("Authentication error")

        monkeypatch.setattr("litellm.completion", mock_completion)
        svc = LiteLLMService(api_key=None)
        assert svc.is_available() is False

    # Tests is_available with Gemini API key from environment variable
    def test_is_available_with_env_api_key_gemini(self, monkeypatch):
        # Mock the completion call to return a successful response
        def mock_completion(*args, **kwargs):
            return {"choices": [{"message": {"content": "test"}}]}

        monkeypatch.setattr("litellm.completion", mock_completion)
        monkeypatch.setenv("GEMINI_API_KEY", "env-test-key")
        svc = LiteLLMService(
            api_key=None, llm_provider="gemini", llm_model="gemini/gemini-2.0-flash"
        )
        assert os.environ.get("GEMINI_API_KEY") == "env-test-key"
        assert svc.is_available() is True

    # Tests is_available with Anthropic API key from environment variable
    def test_is_available_with_env_api_key_anthropic(self, monkeypatch):
        # Mock the completion call to return a successful response
        def mock_completion(*args, **kwargs):
            return {"choices": [{"message": {"content": "test"}}]}

        monkeypatch.setattr("litellm.completion", mock_completion)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-test-key")
        svc = LiteLLMService(llm_provider="anthropic", llm_model="claude-3-sonnet-20240229")
        assert os.environ.get("ANTHROPIC_API_KEY") == "env-test-key"
        assert svc.is_available() is True

    # Tests is_available with OpenAI API key from environment variable
    def test_is_available_with_env_api_key_openai(self, monkeypatch):
        # Mock the completion call to return a successful response
        def mock_completion(*args, **kwargs):
            return {"choices": [{"message": {"content": "test"}}]}

        monkeypatch.setattr("litellm.completion", mock_completion)
        monkeypatch.setenv("OPENAI_API_KEY", "env-test-key")
        svc = LiteLLMService(llm_provider="openai", llm_model="gpt-4o")
        assert os.environ.get("OPENAI_API_KEY") == "env-test-key"
        assert svc.is_available() is True
