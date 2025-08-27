"""Tests for the LLMAnalyzer class."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from arazzo_generator.analyzers.llm_analyzer import LLMAnalyzer


class TestLLMAnalyzer(unittest.TestCase):
    """Tests for the LLMAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample data for testing
        self.endpoints = {
            "/pets": {
                "get": {
                    "operation_id": "listPets",
                    "summary": "List all pets",
                    "tags": ["pet"],
                },
            },
            "/pets/{petId}": {
                "get": {
                    "operation_id": "getPetById",
                    "summary": "Get a pet by ID",
                    "tags": ["pet"],
                }
            },
        }

        self.schemas = {"Pet": {"type": "object"}}
        self.parameters = {"petId": {"type": "string"}}
        self.responses = {"200": {"description": "OK"}}
        self.request_bodies = {"PetBody": {"content": {}}}
        self.spec = {"info": {"title": "Pet Store API"}}
        self.relationships = {"/pets": ["/pets/{petId}"]}

        # Load mock LLM response from file
        mock_file_path = os.path.join(os.path.dirname(__file__), "llm_response_mock.txt")
        with open(mock_file_path) as f:
            content = f.read()
            # Extract JSON content from the markdown code block
            json_content = content.strip().replace("```json", "").replace("```", "").strip()
            self.sample_workflows = json.loads(json_content)

    @patch("arazzo_generator.analyzers.llm_analyzer.LiteLLMService")
    def test_init(self, mock_llm_service_class):
        """Test initialization of the LLMAnalyzer."""
        # Create analyzer with default provider
        analyzer = LLMAnalyzer(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
            self.spec,
            self.relationships,
        )

        # Verify that the LiteLMService was initialized with the default provider
        mock_llm_service_class.assert_called_once()
        self.assertEqual(analyzer.endpoints, self.endpoints)
        self.assertEqual(analyzer.schemas, self.schemas)
        self.assertEqual(analyzer.parameters, self.parameters)
        self.assertEqual(analyzer.responses, self.responses)
        self.assertEqual(analyzer.request_bodies, self.request_bodies)
        self.assertEqual(analyzer.spec, self.spec)
        self.assertEqual(analyzer.relationships, self.relationships)

        # Reset the mock for the next test
        mock_llm_service_class.reset_mock()

        # Test initialization with custom provider and model
        analyzer = LLMAnalyzer(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
            self.spec,
            self.relationships,
            api_key="test_key",
            llm_model="test_model",
            llm_provider="openai",
        )

        # Verify that the LiteLLMService was initialized with the custom provider and model
        mock_llm_service_class.assert_called_once_with(
            api_key="test_key", llm_model="test_model", llm_provider="openai"
        )

    @patch("arazzo_generator.analyzers.llm_analyzer.LiteLLMService")
    def test_is_available(self, mock_llm_service_class):
        """Test the is_available method."""
        # Configure the mock
        mock_service = MagicMock()
        mock_llm_service_class.return_value = mock_service

        # Test when the service is available
        mock_service.is_available.return_value = True
        analyzer = LLMAnalyzer(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
        )
        self.assertTrue(analyzer.is_available())
        mock_service.is_available.assert_called_once()

        # Reset mocks
        mock_service.reset_mock()
        mock_llm_service_class.reset_mock()

        # Test when the service is not available
        mock_service = MagicMock()
        mock_llm_service_class.return_value = mock_service
        mock_service.is_available.return_value = False
        analyzer = LLMAnalyzer(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
        )
        self.assertFalse(analyzer.is_available())
        mock_service.is_available.assert_called_once()

    @patch("arazzo_generator.analyzers.llm_analyzer.LiteLLMService")
    def test_analyze_service_available(self, mock_llm_service_class):
        """Test the analyze method when the LLM service is available."""
        # Configure the mock
        mock_service = MagicMock()
        mock_llm_service_class.return_value = mock_service
        mock_service.is_available.return_value = True
        mock_service.analyze_endpoints.return_value = self.sample_workflows

        # Create analyzer and call analyze
        analyzer = LLMAnalyzer(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
            self.spec,
        )
        result = analyzer.analyze()

        # Verify that the service methods were called correctly
        mock_service.is_available.assert_called_once()
        mock_service.analyze_endpoints.assert_called_once_with(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
            self.spec,
            user_workflow_descriptions=None,
        )

        # Verify the result
        self.assertEqual(result, self.sample_workflows)
        self.assertEqual(analyzer.workflows, self.sample_workflows)

        # Verify the structure of the returned workflows
        self.assertGreaterEqual(len(result), 1)
        workflow = result[0]
        self.assertIn("name", workflow)
        self.assertIn("description", workflow)
        self.assertIn("type", workflow)
        self.assertIn("operations", workflow)
        self.assertGreaterEqual(len(workflow["operations"]), 1)
        operation = workflow["operations"][0]
        # Check for required operation fields
        self.assertIn("method", operation)
        self.assertIn("path", operation)
        self.assertIn("operation_id", operation)
        self.assertIn("summary", operation)
        self.assertIn("tags", operation)

    @patch("arazzo_generator.analyzers.llm_analyzer.LiteLLMService")
    def test_analyze_service_not_available(self, mock_llm_service_class):
        """Test the analyze method when the LLM service is not available."""
        # Configure the mock
        mock_service = MagicMock()
        mock_llm_service_class.return_value = mock_service
        mock_service.is_available.return_value = False

        # Create analyzer and call analyze
        analyzer = LLMAnalyzer(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
        )
        result = analyzer.analyze()

        # Verify that the service methods were called correctly
        mock_service.is_available.assert_called_once()
        mock_service.analyze_endpoints.assert_not_called()

        # Verify the result
        self.assertEqual(result, [])
        self.assertEqual(analyzer.workflows, [])

    @patch("arazzo_generator.analyzers.llm_analyzer.LiteLLMService")
    def test_analyze_service_exception(self, mock_llm_service_class):
        """Test the analyze method when the LLM service raises an exception."""
        # Configure the mock
        mock_service = MagicMock()
        mock_llm_service_class.return_value = mock_service
        mock_service.is_available.return_value = True
        mock_service.analyze_endpoints.side_effect = Exception("Test exception")

        # Create analyzer and call analyze
        analyzer = LLMAnalyzer(
            self.endpoints,
            self.schemas,
            self.parameters,
            self.responses,
            self.request_bodies,
        )
        result = analyzer.analyze()

        # Verify that the service methods were called correctly
        mock_service.is_available.assert_called_once()
        mock_service.analyze_endpoints.assert_called_once()

        # Verify the result
        self.assertEqual(result, [])
        self.assertEqual(analyzer.workflows, [])


if __name__ == "__main__":
    unittest.main()
