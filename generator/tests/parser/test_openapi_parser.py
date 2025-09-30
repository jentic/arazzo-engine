"""Tests for the OpenAPI parser module."""

import unittest
from unittest.mock import patch

from arazzo_generator.parser.openapi_parser import OpenAPIParser


class TestOpenAPIParser(unittest.TestCase):
    """Tests for the OpenAPIParser class."""

    def setUp(self):
        """Set up the test case."""
        # Reset any class variables or state before each test
        pass

    @patch.object(OpenAPIParser, "_fetch_and_parse_with_fallbacks")
    def test_fetch_spec_json(self, mock_fetch):
        """Test fetching a JSON OpenAPI spec."""
        # Prepare test data
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

        # Configure the mock to return our test data
        mock_fetch.return_value = test_spec

        # Create parser and fetch spec
        parser = OpenAPIParser("https://example.com/openapi.json")
        spec = parser.fetch_spec()

        # Check that the spec was parsed correctly
        self.assertEqual(spec["openapi"], "3.0.0")
        self.assertEqual(spec["info"]["title"], "Test API")
        self.assertEqual(spec["paths"]["/test"]["get"]["operationId"], "getTest")

        # Check that the metadata was extracted
        self.assertEqual(parser.version, "3.0.0")
        self.assertIn("/test", parser.paths)

    @patch.object(OpenAPIParser, "_fetch_and_parse_with_fallbacks")
    def test_fetch_spec_yaml(self, mock_fetch):
        """Test fetching a YAML OpenAPI spec."""
        # Prepare test data
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

        # Configure the mock to return our test data
        mock_fetch.return_value = test_spec

        # Create parser and fetch spec
        parser = OpenAPIParser("https://example.com/openapi.yaml")
        spec = parser.fetch_spec()

        # Check that the spec was parsed correctly
        self.assertEqual(spec["openapi"], "3.0.0")
        self.assertEqual(spec["info"]["title"], "Test API")
        self.assertEqual(spec["paths"]["/test"]["get"]["operationId"], "getTest")

    @patch.object(OpenAPIParser, "_fetch_and_parse_with_fallbacks")
    def test_get_endpoints(self, mock_fetch):
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

        # Configure the mock to return our test data
        mock_fetch.return_value = test_spec

        # Create a new parser instance for this test
        parser = OpenAPIParser("https://example.com/openapi.json")
        parser.fetch_spec()  # This will use the mock

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

    @patch.object(OpenAPIParser, "_fetch_and_parse_with_fallbacks")
    def test_get_schemas(self, mock_fetch):
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

        # Configure the mock to return our test data
        mock_fetch.return_value = test_spec

        # Create a new parser instance for this test
        parser = OpenAPIParser("https://example.com/openapi.json")
        parser.fetch_spec()  # This will use the mock

        # Get schemas
        schemas = parser.get_schemas()

        # Check that the schemas were extracted correctly
        self.assertIn("User", schemas)
        self.assertEqual(schemas["User"]["type"], "object")
        self.assertIn("id", schemas["User"]["properties"])
        self.assertIn("name", schemas["User"]["properties"])

    @patch.object(OpenAPIParser, "_fetch_and_parse_with_fallbacks")
    def test_get_security_schemes(self, mock_fetch):
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

        # Configure the mock to return our test data
        mock_fetch.return_value = test_spec

        # Create a new parser instance for this test
        parser = OpenAPIParser("https://example.com/openapi.json")
        parser.fetch_spec()  # This will use the mock

        # Get security schemes
        security_schemes = parser.get_security_schemes()

        # Check that the security schemes were extracted correctly
        self.assertIn("bearerAuth", security_schemes)
        self.assertEqual(security_schemes["bearerAuth"]["type"], "http")
        self.assertEqual(security_schemes["bearerAuth"]["scheme"], "bearer")
        self.assertEqual(security_schemes["bearerAuth"]["bearerFormat"], "JWT")

    def test_clean_spec_content_utf8_bom(self):
        """Test UTF-8 BOM removal."""
        parser = OpenAPIParser("dummy_url")
        content_with_bom = "\ufeff{\"openapi\": \"3.0.0\"}"
        cleaned = parser._clean_spec_content(content_with_bom)
        self.assertFalse(cleaned.startswith("\ufeff"))
        self.assertTrue(cleaned.startswith("{"))

    def test_clean_spec_content_smart_quotes(self):
        """Test smart quotes replacement."""
        parser = OpenAPIParser("dummy_url")
        content_with_smart_quotes = '“openapi”: “3.0.0”'
        cleaned = parser._clean_spec_content(content_with_smart_quotes)
        self.assertIn('"openapi": "3.0.0"', cleaned)

    def test_clean_spec_content_windows_line_endings(self):
        """Test CRLF to LF conversion."""
        parser = OpenAPIParser("dummy_url")
        content_with_crlf = "{\r\n\"openapi\": \"3.0.0\"\r\n}"
        cleaned = parser._clean_spec_content(content_with_crlf)
        self.assertNotIn('\r\n', cleaned)
        self.assertIn('\n', cleaned)

    def test_clean_spec_content_non_breaking_spaces(self):
        """Test non-breaking spaces conversion."""
        parser = OpenAPIParser("dummy_url")
        content_with_nbsp = "{\u00a0\"openapi\":\u00a0\"3.0.0\"\u00a0}"
        cleaned = parser._clean_spec_content(content_with_nbsp)
        self.assertNotIn('\u00a0', cleaned)
        self.assertIn(' ', cleaned)

    def test_clean_spec_content_dash_characters(self):
        """Test en-dash and em-dash conversion."""
        parser = OpenAPIParser("dummy_url")
        content_with_dashes = '{"desc": "en–dash, em—dash"}'
        cleaned = parser._clean_spec_content(content_with_dashes)
        self.assertNotIn('–', cleaned)
        self.assertNotIn('—', cleaned)
        self.assertIn('-', cleaned)
