"""Tests for the OpenAPI parser module."""

import unittest
from unittest.mock import patch
import textwrap

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

    def test_fix_missing_spaces_after_colons(self):
        """Test fixing missing spaces after colons in YAML content."""

        def _T(s: str) -> str:
            """Dedent and trim trailing newline, so comparisons don't depend on final LF."""
            return textwrap.dedent(s).strip('\n')

        def assertFix(before: str, after: str):
            self.assertEqual(OpenAPIParser._fix_missing_spaces_after_colons(_T(before)),
                             _T(after))

        # --- basic fixes & no-ops ---

        # def test_simple_mapping_needs_fix
        assertFix(
            """
            foo:bar
            baz: qux
            """,
            """
            foo: bar
            baz: qux
            """
        )

        # def test_already_spaced_is_untouched
        assertFix(
            """
            a: b
            nested:
              c: d
            """,
            """
            a: b
            nested:
              c: d
            """
        )

        # def test_tab_after_colon_is_respected
        # If the next char is a tab, it's treated like whitespace and should not add a space
        assertFix(
            "a:\tb",
            "a:\tb",
        )

        # --- lists & flow collections ---

        # def test_list_item_key_value
        assertFix(
            """
            - name:Francesco
            - age:42
            - city: Trieste
            """,
            """
            - name: Francesco
            - age: 42
            - city: Trieste
            """
        )

        # def test_flow_mapping_internal_pairs_untouched_outer_fixed
        assertFix(
            """
            person:{name:John,age:30}
            """,
            """
            person: {name:John,age:30}
            """
        )

        # def test_space_before_flow_sequence
        assertFix(
            """
            tags:[a,b,c]
            """,
            """
            tags: [a,b,c]
            """
        )

        # --- quotes, escapes, and comments ---

        # def test_colon_inside_quotes_untouched
        assertFix(
            """
            time: "10:30"
            note: 'a: b'
            path: "C:\\Temp\\foo:bar"
            """,
            """
            time: "10:30"
            note: 'a: b'
            path: "C:\\Temp\\foo:bar"
            """
        )

        # def test_quoted_keys_with_spaces
        assertFix(
            """
            "full name":Francesco
            'with space':value
            """,
            """
            "full name": Francesco
            'with space': value
            """
        )

        # def test_unquoted_key_with_space_is_not_considered_key
        # Unquoted key containing space should not be auto-fixed
        assertFix(
            """
            first name:Francesco
            """,
            """
            first name:Francesco
            """
        )

        # def test_inline_comment_region_is_ignored
        assertFix(
            """
            a:b  # comment with a:colon that should be ignored
            """,
            """
            a: b  # comment with a:colon that should be ignored
            """
        )

        # def test_hash_in_quotes_not_a_comment
        assertFix(
            """
            msg: "value # not a comment"
            msg2:"another #test"
            """,
            """
            msg: "value # not a comment"
            msg2: "another #test"
            """
        )

        # --- URL and scheme-like values ---


        # --- Misc, edge behavior ---

        # def test_malformed_brackets_do_not_cause_crash
        # There is internal reset if counters go negative; behavior here is just "no crash"
        assertFix(
            """
            a:b]
            c:{d:e
            """,
            """
            a: b]
            c: {d:e
            """
        )

        # def test_blank_and_full_line_comments_untouched
        assertFix(
            """
            # top level comment
            key:value
              # indented comment
            """,
            """
            # top level comment
            key: value
              # indented comment
            """
        )

        # def test_multiple_colons_fix_only_first_key_value
        assertFix(
            """
            a:b:c
            """,
            """
            a: b:c
            """
        )

        # def test_url_and_ports_in_value
        # Should fix the key colon; leave scheme/port colons in the value untouched
        assertFix(
            """
            endpoint:http://example.com:8080/api
            repo: git://github.com/org/repo.git
            email:mailto:user@example.com
            """,
            """
            endpoint: http://example.com:8080/api
            repo: git://github.com/org/repo.git
            email: mailto:user@example.com
            """
        )

        # def test_dashes_without_space
        # Accept some flexible spacing after '-' per implementation
        assertFix(
            """
            -name:value
            -  title:Engineer
            """,
            """
            - name: value
            -  title: Engineer
            """
        )

        """
        Ideally, lines inside a literal block should be treated as plain text,
        and not receive key:value fixes. Current implementation will modify them.
        """
        before = _T(
            """
            description: |
              url:http://example.com
              note:keep as-is
            """
        )
        # Desired (no change inside the block):
        desired = before
        self.assertNotEqual(OpenAPIParser._fix_missing_spaces_after_colons(before), desired)
