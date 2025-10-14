#!/usr/bin/env python3
"""
Tests for the Arazzo Runner library

This file contains basic tests for the Arazzo Runner library. For more comprehensive
testing with fixtures, see test_fixture_discovery.py which implements an automatic
fixture-based testing framework.
"""

import json
import os
import tempfile
import unittest
from urllib.parse import urlparse

import yaml

# Use the new namespace for imports
from arazzo_runner import ArazzoRunner, ExecutionState, StepStatus, WorkflowExecutionStatus


class MockHTTPExecutor:
    """Mock HTTP client for testing, supporting headers, params, and JSON payloads"""

    def __init__(self, mock_responses=None, default_headers=None):
        """
        Args:
            mock_responses (dict): keys are tuples (method, url), values are MockResponse
            default_headers (dict): headers to include in every request
        """
        self.mock_responses = mock_responses or {}
        self.default_headers = default_headers or {}
        self.requests = []

    def request(self, method, url, **kwargs):
        """
        Record the request and return a mock response.
        Supports 'params', 'headers', and 'json' keyword arguments.
        """
        # Merge default headers with request-specific headers
        headers = self.default_headers.copy()
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        # Record the request
        self.requests.append({"method": method.lower(), "url": url, "kwargs": kwargs})

        # Determine response
        key = (method.lower(), url)
        response = self.mock_responses.get(key)
        if response:
            return response

        # Default 404 response
        return MockResponse(404, {"error": "Not found"})


class MockResponse:
    """Mock HTTP response for testing"""

    def __init__(self, status_code, json_data=None, text=None, headers=None, content=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or ""
        self.headers = headers or {}
        if json_data is not None and not any(k.lower() == "content-type" for k in self.headers):
            self.headers["Content-Type"] = "application/json"

        if content is not None:
            self.content = content
        elif self._json_data is not None:
            self.content = json.dumps(self._json_data).encode("utf-8")
        elif self.text:
            self.content = self.text.encode("utf-8")
        else:
            self.content = b""

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON data")
        return self._json_data

    def raise_for_status(self):
        """Raise an exception if status code is 4XX or 5XX"""
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP Error: {self.status_code}")


class TestArazzoRunner(unittest.TestCase):
    """Test the Arazzo Runner functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.openapi_path = os.path.join(self.temp_dir.name, "test_openapi.yaml")
        self.arazzo_path = os.path.join(self.temp_dir.name, "test_workflow.yaml")

        # OpenAPI spec
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "description": "API for testing", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {
                "/login": {
                    "post": {
                        "operationId": "loginUser",
                        "summary": "Log in a user",
                        "parameters": [],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "username": {"type": "string"},
                                            "password": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "Success"}},
                    }
                },
                "/data": {
                    "get": {
                        "operationId": "getData",
                        "summary": "Get data",
                        "parameters": [
                            {"name": "filter", "in": "query", "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "Success"}},
                    }
                },
            },
        }
        with open(self.openapi_path, "w") as f:
            yaml.dump(self.openapi_spec, f)

        # Arazzo workflow
        self.arazzo_doc = {
            "arazzo": "1.0.0",
            "info": {"title": "Test Workflow", "description": "A workflow for testing", "version": "1.0.0"},
            "sourceDescriptions": [{"name": "testApi", "url": self.openapi_path, "type": "openapi"}],
            "workflows": [
                {
                    "workflowId": "testWorkflow",
                    "summary": "Test workflow",
                    "description": "A workflow for testing",
                    "inputs": {
                        "type": "object",
                        "properties": {"username": {"type": "string"}, "password": {"type": "string"}, "filter": {"type": "string"}},
                    },
                    "steps": [
                        {
                            "stepId": "loginStep",
                            "description": "Login step",
                            "operationId": "loginUser",
                            "requestBody": {
                                "contentType": "application/json",
                                "payload": {"username": "$inputs.username", "password": "$inputs.password"},
                            },
                            "successCriteria": [{"condition": "$statusCode == 200"}],
                            "outputs": {"token": "$response.body.token"},
                        },
                        {
                            "stepId": "getDataStep",
                            "description": "Get data step",
                            "operationId": "getData",
                            "parameters": [
                                {"name": "filter", "in": "query", "value": "$inputs.filter"},
                                {"name": "Authorization", "in": "header", "value": "Bearer $steps.loginStep.outputs.token"},
                            ],
                            "successCriteria": [{"condition": "$statusCode == 200"}],
                            "outputs": {"data": "$response.body.items"},
                        },
                    ],
                    "outputs": {"result": "$steps.getDataStep.outputs.data"},
                }
            ],
        }
        with open(self.arazzo_path, "w") as f:
            yaml.dump(self.arazzo_doc, f)

        # Mock HTTP client
        self.http_client = MockHTTPExecutor(
            {
                ("post", "https://api.example.com/v1/login"): MockResponse(200, {"token": "test-token-123"}),
                ("get", "https://api.example.com/v1/data"): MockResponse(200, {"items": [{"id": 1}, {"id": 2}]}),
            }
        )

        self.runner = ArazzoRunner(
            arazzo_doc=self.arazzo_doc,
            source_descriptions={"testApi": self.openapi_spec},
            http_client=self.http_client,
        )

    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()

    def test_execute_workflow(self):
        """Test executing a complete workflow with request validation"""
        inputs = {"username": "testuser", "password": "password123", "filter": "test"}
        execution_id = self.runner.start_workflow("testWorkflow", inputs)

        # Execute first step (login)
        result1 = self.runner.execute_next_step(execution_id)
        req1 = self.http_client.requests[0]

        # Validate request method, URL, headers, and payload
        self.assertEqual(req1["method"], "post")
        self.assertEqual(req1["url"], "https://api.example.com/v1/login")
        self.assertEqual(req1["kwargs"]["json"], {"username": "testuser", "password": "password123"})
        self.assertIn("Content-Type", req1["kwargs"]["headers"])

        # Execute second step (getData)
        result2 = self.runner.execute_next_step(execution_id)
        req2 = self.http_client.requests[1]

        # Validate request method, URL, headers, and query params
        self.assertEqual(req2["method"], "get")
        self.assertEqual(req2["url"], "https://api.example.com/v1/data")
        self.assertEqual(req2["kwargs"]["params"], {"filter": "test"})
        self.assertTrue(req2["kwargs"]["headers"]["Authorization"].startswith("Bearer "))

        # Complete workflow
        result3 = self.runner.execute_next_step(execution_id)
        self.assertEqual(result3["status"], WorkflowExecutionStatus.WORKFLOW_COMPLETE)
        self.assertIn("outputs", result3)

    # -------------------
    # New Tests for URL Loading
    # -------------------

    def test_load_arazzo_from_url(self):
        """Test loading an Arazzo workflow JSON file from a remote URL"""
        remote_url = "https://mockserver.com/workflows/test_workflow.arazzo.json"

        # Mock the remote workflow content
        mock_arazzo_json = json.dumps(self.arazzo_doc)
        self.http_client.mock_responses[("get", remote_url)] = MockResponse(200, text=mock_arazzo_json)

        # Initialize runner with URL
        runner_url = ArazzoRunner(
            arazzo_doc=remote_url,
            source_descriptions={"testApi": self.openapi_spec},
            http_client=self.http_client,
        )

        # Start workflow and execute a step
        inputs = {"username": "urluser", "password": "urlpass", "filter": "urltest"}
        execution_id = runner_url.start_workflow("testWorkflow", inputs)
        result1 = runner_url.execute_next_step(execution_id)

        self.assertEqual(result1["status"], WorkflowExecutionStatus.STEP_COMPLETE)
        self.assertEqual(result1["step_id"], "loginStep")

    def test_load_source_from_url(self):
        """Test loading an OpenAPI source description from a remote URL"""
        remote_openapi_url = "https://mockserver.com/apis/test_openapi.yaml"

        # Mock the OpenAPI YAML content
        mock_openapi_yaml = yaml.dump(self.openapi_spec)
        self.http_client.mock_responses[("get", remote_openapi_url)] = MockResponse(200, text=mock_openapi_yaml)

        # Arazzo doc with remote source
        arazzo_doc_remote_source = self.arazzo_doc.copy()
        arazzo_doc_remote_source["sourceDescriptions"] = [{"name": "testApi", "url": remote_openapi_url, "type": "openapi"}]

        # Initialize runner
        runner_remote_source = ArazzoRunner(
            arazzo_doc=arazzo_doc_remote_source,
            source_descriptions={},  # empty dict, will fetch from URL
            http_client=self.http_client,
        )

        # Start workflow and execute a step
        inputs = {"username": "urluser", "password": "urlpass", "filter": "urltest"}
        execution_id = runner_remote_source.start_workflow("testWorkflow", inputs)
        result1 = runner_remote_source.execute_next_step(execution_id)

        self.assertEqual(result1["status"], WorkflowExecutionStatus.STEP_COMPLETE)
        self.assertEqual(result1["step_id"], "loginStep")


if __name__ == "__main__":
    unittest.main()
