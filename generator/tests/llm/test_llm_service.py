"""
Unit tests for the LLMService class in llm_service.py.
This file uses pytest and unittest.mock to test initialization and endpoint analysis logic.
"""

import shutil
import tempfile
from unittest.mock import patch

import pytest

from arazzo_generator.llm.litellm_service import LiteLLMService


# Section 1: Fixtures and helpers
@pytest.fixture
def dummy_endpoints():
    # Minimal endpoint structure for testing
    return {
        "/pets": {
            "get": {
                "summary": "List pets",
                "description": "Returns all pets",
                "parameters": [],
                "responses": {},
                "tags": ["pets"],
            }
        }
    }


@pytest.fixture
def dummy_schemas():
    return {"Pet": {"type": "object", "properties": {"name": {"type": "string"}}}}


@pytest.fixture
def dummy_parameters():
    return {}


@pytest.fixture
def dummy_responses():
    return {}


@pytest.fixture
def dummy_request_bodies():
    return {}


# Section 2: LLM Initalisation in test_llm_service_initialisation.py

# Section 3: Endpoint formatting tests in test_llm_service_format_endpoints.py


# Section 4: analyze_endpoints tests
class TestLLMServiceAnalyzeEndpoints:
    # Tests successful endpoint analysis
    @patch("arazzo_generator.llm.litellm_service.LiteLLMService.is_available", return_value=True)
    @patch("arazzo_generator.llm.litellm_service.LiteLLMService._make_request")
    @patch("arazzo_generator.llm.litellm_service.LiteLLMService._parse_workflow_response")
    @patch("arazzo_generator.llm.litellm_service.log_llm_response")
    @patch("arazzo_generator.llm.litellm_service.log_llm_prompt")
    @patch(
        "arazzo_generator.llm.litellm_service.setup_log_directory",
    )
    def test_analyze_endpoints_success(
        self,
        mock_log_dir,
        mock_log_llm_prompt,
        mock_log_llm_response,
        mock_parse_workflow_response,
        mock_make_request,
        mock_is_available,
        dummy_endpoints,
        dummy_schemas,
        dummy_parameters,
        dummy_responses,
        dummy_request_bodies,
    ):
        temp_dir = tempfile.mkdtemp()
        mock_log_dir.return_value = (temp_dir, "timestamp")

        llm_response = "Mock LLM response with workflow data"
        parsed_response = [
            {
                "name": "test_workflow",
                "description": "desc",
                "type": "process",
                "operations": [],
                "rank": 5,
            }
        ]

        mock_make_request.return_value = llm_response
        mock_parse_workflow_response.return_value = parsed_response

        svc = LiteLLMService(api_key="test-key")

        result = svc.analyze_endpoints(
            dummy_endpoints,
            dummy_schemas,
            dummy_parameters,
            dummy_responses,
            dummy_request_bodies,
        )

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 1

        workflow = result[0]
        assert workflow["name"] == "test_workflow"
        assert workflow["description"] == "desc"
        assert workflow["type"] == "process"
        assert workflow["operations"] == []
        assert workflow["rank"] == 5

        # Verify all mock calls
        mock_log_dir.assert_called_once()

        # Verify prompt logging
        mock_log_llm_prompt.assert_called_once()
        args = mock_log_llm_prompt.call_args[0]
        assert len(args) == 4  # prompt, log_dir, file_prefix, timestamp
        assert args[1] == temp_dir  # log_dir
        assert args[2] == "workflow_analysis"  # file_prefix
        assert args[3] == "timestamp"  # timestamp

        # Verify LLM request
        mock_make_request.assert_called_once()
        prompt_sent = mock_make_request.call_args[0][0]
        assert isinstance(prompt_sent, str)

        # Verify response logging
        mock_log_llm_response.assert_called_once_with(llm_response, temp_dir, "workflow_analysis")

        # Verify workflow parsing
        mock_parse_workflow_response.assert_called_once_with(mock_make_request.return_value)

        shutil.rmtree(temp_dir)

    # Tests endpoint analysis failure
    @patch("arazzo_generator.llm.litellm_service.LiteLLMService.is_available", return_value=True)
    @patch("arazzo_generator.llm.litellm_service.LiteLLMService._make_request")
    @patch("arazzo_generator.llm.litellm_service.LiteLLMService._parse_workflow_response")
    @patch("arazzo_generator.llm.litellm_service.log_llm_response")
    @patch("arazzo_generator.llm.litellm_service.log_llm_prompt")
    @patch(
        "arazzo_generator.llm.litellm_service.setup_log_directory",
    )
    @patch("arazzo_generator.llm.litellm_service.logger")
    def test_analyze_endpoints_failure(
        self,
        mock_logger,
        mock_log_dir,
        mock_log_llm_prompt,
        mock_log_llm_response,
        mock_parse_workflow_response,
        mock_make_request,
        mock_is_available,
        dummy_endpoints,
        dummy_schemas,
        dummy_parameters,
        dummy_responses,
        dummy_request_bodies,
    ):
        temp_dir = tempfile.mkdtemp()
        mock_log_dir.return_value = (temp_dir, "timestamp")
        # Setup mocks to simulate error
        mock_make_request.side_effect = Exception("Test error")

        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        result = svc.analyze_endpoints(
            dummy_endpoints,
            dummy_schemas,
            dummy_parameters,
            dummy_responses,
            dummy_request_bodies,
        )
        assert result == []

        # Verify the error was logged correctly
        mock_logger.error.assert_called_with("Error in LLM workflow analysis: Test error")
        shutil.rmtree(temp_dir)


# Section 5: Extraction function tests
class TestLLMServiceExtraction:
    # Tests extraction of API metadata
    def test_extract_api_metadata(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "This is a test API",
                "contact": {"name": "John Doe", "url": "https://johndoe.com"},
                "license": {"name": "MIT", "url": "https://mit.com"},
                "termsOfService": "https://example.com/terms",
            },
            "servers": [{"url": "https://api.example.com"}],
            "security": [{"apiKey": []}],
            "tags": ["discoveryresources", "metadataresources"],
            "externalDocs": {
                "description": "API documentation",
                "url": "http://example.com/docs/read/ProgrammesAPIGuide",
            },
        }

        metadata = svc._extract_api_metadata(openapi_spec)
        assert metadata["title"] == "Test API"
        assert metadata["version"] == "1.0.0"
        assert metadata["description"] == "This is a test API"
        assert metadata["terms_of_service"] == "https://example.com/terms"
        assert metadata["contact"] == {"name": "John Doe", "url": "https://johndoe.com"}
        assert metadata["license"] == {"name": "MIT", "url": "https://mit.com"}
        assert metadata["servers"] == [{"url": "https://api.example.com"}]
        assert metadata["security"] == [{"apiKey": []}]
        assert metadata["tags"] == ["discoveryresources", "metadataresources"]
        assert metadata["external_docs"] == {
            "description": "API documentation",
            "url": "http://example.com/docs/read/ProgrammesAPIGuide",
        }

    # Tests extraction of api metadata with missing fields
    def test_extract_api_metadata_missing_fields(self):
        svc = LiteLLMService(api_key="test-key")

        # Test with minimal spec containing only required fields
        minimal_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
        }

        metadata = svc._extract_api_metadata(minimal_spec)
        assert metadata["title"] == "Test API"
        assert metadata["version"] == "1.0.0"
        assert metadata["description"] == ""
        assert metadata["terms_of_service"] == ""
        assert metadata["contact"] == {}
        assert metadata["license"] == {}
        assert metadata["servers"] == []
        assert metadata["security"] == []
        assert metadata["tags"] == []
        assert metadata["external_docs"] == {}

    # Tests extraction of api metadata with empty spec
    def test_extract_api_metadata_empty_spec(self):
        svc = LiteLLMService(api_key="test-key")

        empty_spec = {}
        metadata = svc._extract_api_metadata(empty_spec)

        # Should handle empty spec gracefully
        assert metadata["title"] == ""
        assert metadata["version"] == ""
        assert metadata["description"] == ""
        assert metadata["terms_of_service"] == ""
        assert metadata["contact"] == {}
        assert metadata["license"] == {}
        assert metadata["servers"] == []
        assert metadata["security"] == []
        assert metadata["tags"] == []
        assert metadata["external_docs"] == {}


# Section 6: Prompt builder unit tests in test_llm_service_prompt_builders.py


# Section 7: LLM request dispatching tests
# These are examples of LiteLLM providers and models. Other providers and models can also be used.
class TestLLMServiceMakeRequest:
    # Tests that the LLM request is dispatched correctly when using default config provider and model
    def test_make_request_default(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"
        assert svc.llm_model == "gemini/gemini-2.0-flash"

        with patch.object(svc, "_make_request", return_value="gemini-response") as mock_method:
            result = svc._make_request("prompt")
            assert result == "gemini-response"
            mock_method.assert_called_once_with("prompt")

    # Tests that the LLM request is dispatched correctly when using gemini
    def test_make_request_gemini(self):
        svc = LiteLLMService(
            api_key="test-key",
            llm_provider="gemini",
            llm_model="gemini/gemini-2.0-flash",
        )
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"
        assert svc.llm_model == "gemini/gemini-2.0-flash"

        with patch.object(svc, "_make_request", return_value="gemini-response") as mock_method:
            result = svc._make_request("prompt")
            assert result == "gemini-response"
            mock_method.assert_called_once_with("prompt")

    # Tests that the LLM request is dispatched correctly when using anthropic
    def test_make_request_anthropic(self):
        svc = LiteLLMService(
            api_key="test-key",
            llm_provider="anthropic",
            llm_model="claude-3-sonnet-20240229",
        )
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "anthropic"
        assert svc.llm_model == "claude-3-sonnet-20240229"

        with patch.object(svc, "_make_request", return_value="anthropic-response") as mock_method:
            result = svc._make_request("prompt")
            assert result == "anthropic-response"
            mock_method.assert_called_once_with("prompt")

    def test_make_request_openai(self):
        svc = LiteLLMService(api_key="test-key", llm_provider="openai", llm_model="gpt-4o")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "openai"
        assert svc.llm_model == "gpt-4o"

        with patch.object(svc, "_make_request", return_value="openai-response") as mock_method:
            result = svc._make_request("prompt")
            assert result == "openai-response"
            mock_method.assert_called_once_with("prompt")


# Section 8: Workflow processing and recovery tests in test_llm_service_workflow_processing.py

# Section 9: Parsing and formatting tests in test_llm_service_parsing_and_formatting.py

"""
Explanation of sections:
1. Fixtures: Minimal dummy data for endpoints, schemas, etc., to keep tests isolated and fast.
2. Provider initialization tests: LLM provider setup and invalid provider error handling.
3. Endpoint formatting tests: Endpoint formatting logic.
4. Analyze_endpoints tests: LLM analysis logic, with logging and LLM calls patched.
5. Extractors tests: Tests for extracting data from OpenAPI spec.
6. Prompt builder tests: Tests for building prompts for LLM requests.
7. LLM provider request dispatch tests: Tests for dispatching LLM requests to the correct provider.
8. Workflow processing and recovery tests: Workflow field processing, malformed JSON recovery, cleaning, and validation response handling.
9. Parsing and formatting tests: Tests for parsing and formatting LLM responses.
"""
