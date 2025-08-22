"""Tests for the OpenAPI parser module."""

import unittest
from unittest.mock import patch, MagicMock
import json

from arazzo_generator.parser.openapi_parser import OpenAPIParser


@patch('requests.get')
class TestOpenAPIParser(unittest.TestCase):
    """Tests for the OpenAPIParser class."""

    def setUp(self):
        """Set up the test case."""
        # Reset any class variables or state before each test
        pass

    def test_fetch_spec_json(self, mock_requests_get):
        """Test fetching a JSON OpenAPI spec from a URL."""
        test_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "getTest",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(test_spec).encode('utf-8')
        mock_response.text = json.dumps(test_spec)
        mock_requests_get.return_value = mock_response

        parser = OpenAPIParser("https://example.com/openapi.json")
        spec = parser.fetch_spec()

        # Check that the spec was parsed correctly
        self.assertEqual(spec["openapi"], "3.0.0")
        self.assertEqual(spec["info"]["title"], "Test API")
        self.assertEqual(spec["paths"]["/test"]["get"]["operationId"], "getTest")

        # Check that the metadata was extracted
        self.assertEqual(parser.version, "3.0.0")
        self.assertIn("/test", parser.paths)

    def test_fetch_spec_yaml(self, mock_requests_get):
        """Test fetching a YAML OpenAPI spec from a URL."""
        test_spec_yaml = """
        openapi: 3.0.0
        info:
          title: Test API
          version: 1.0.0
        paths:
          /test:
            get:
              operationId: getTest
              responses:
                200:
                  description: OK
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = test_spec_yaml.encode('utf-8')
        mock_response.text = test_spec_yaml
        mock_requests_get.return_value = mock_response

        parser = OpenAPIParser("https://example.com/openapi.yaml")
        spec = parser.fetch_spec()

        # Check that the spec was parsed correctly
        self.assertEqual(spec["openapi"], "3.0.0")
        self.assertEqual(spec["info"]["title"], "Test API")
        self.assertEqual(spec["paths"]["/test"]["get"]["operationId"], "getTest")

    @patch('prance.ResolvingParser')
    def test_get_endpoints(self, mock_prance_parser, mock_requests_get):
        """Test getting endpoints from the OpenAPI spec."""
        # Prepare test data with endpoints
        test_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    },
                    "post": {
                        "operationId": "createUser",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    },
                }
            },
        }

        # Configure the prance mock to simulate successful parsing
        mock_parser_instance = MagicMock()
        mock_parser_instance.specification = test_spec
        mock_prance_parser.return_value = mock_parser_instance

        # This mock is no longer strictly needed for this path, but we keep it for consistency
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(test_spec).encode('utf-8')
        mock_response.text = json.dumps(test_spec)
        mock_requests_get.return_value = mock_response

        # Create a new parser instance for this test
        parser = OpenAPIParser("https://example.com/openapi.json")

        # Get endpoints
        endpoints = parser.get_endpoints()

        # Check that the endpoints were extracted correctly
        self.assertIn("/users", endpoints)
        self.assertIn("get", endpoints["/users"])
        self.assertIn("post", endpoints["/users"])
        self.assertEqual(endpoints["/users"]["get"]["operation_id"], "getUsers")
        self.assertEqual(endpoints["/users"]["post"]["operation_id"], "createUser")
        self.assertEqual(len(endpoints["/users"]["get"]["parameters"]), 1)
        self.assertEqual(endpoints["/users"]["get"]["parameters"][0]["name"], "limit")

    @patch('prance.ResolvingParser')
    def test_get_schemas(self, mock_prance_parser, mock_requests_get):
        """Test getting schemas from the OpenAPI spec."""
        # Prepare test data with schemas
        test_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }

        # Configure the prance mock
        mock_parser_instance = MagicMock()
        mock_parser_instance.specification = test_spec
        mock_prance_parser.return_value = mock_parser_instance

        # Configure the requests mock for fallback consistency
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(test_spec).encode('utf-8')
        mock_response.text = json.dumps(test_spec)
        mock_requests_get.return_value = mock_response

        # Create a new parser instance for this test
        parser = OpenAPIParser("https://example.com/openapi.json")

        # Get schemas
        schemas = parser.get_schemas()

        # Check that the schemas were extracted correctly
        self.assertIn("User", schemas)
        self.assertEqual(schemas["User"]["type"], "object")
        self.assertIn("id", schemas["User"]["properties"])
        self.assertIn("name", schemas["User"]["properties"])

    @patch('prance.ResolvingParser')
    def test_get_security_schemes(self, mock_prance_parser, mock_requests_get):
        """Test getting security schemes from the OpenAPI spec."""
        # Prepare test data with security schemes
        test_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                }
            },
        }

        # Configure the prance mock
        mock_parser_instance = MagicMock()
        mock_parser_instance.specification = test_spec
        mock_prance_parser.return_value = mock_parser_instance

        # Configure the requests mock for fallback consistency
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(test_spec).encode('utf-8')
        mock_response.text = json.dumps(test_spec)
        mock_requests_get.return_value = mock_response

        # Create a new parser instance for this test
        parser = OpenAPIParser("https://example.com/openapi.json")

        # Get security schemes
        security_schemes = parser.get_security_schemes()

        # Check that the security schemes were extracted correctly
        self.assertIn("bearerAuth", security_schemes)
        self.assertEqual(security_schemes["bearerAuth"]["type"], "http")
        self.assertEqual(security_schemes["bearerAuth"]["scheme"], "bearer")
        self.assertEqual(security_schemes["bearerAuth"]["bearerFormat"], "JWT")
