import os
import unittest

import yaml

from arazzo_runner.auth.auth_processor import AuthProcessor
from arazzo_runner.auth.models import SecurityOption, SecurityRequirement
from arazzo_runner.executor.operation_finder import OperationFinder

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "test_data")


def _yaml(rel: str) -> dict:
    with open(os.path.join(_FIXTURES_DIR, rel)) as f:
        return yaml.safe_load(f)


MOCK_SOURCE_DESC = {
    "api_one": _yaml("mock_apis/api_one.openapi.yaml"),
    "api_two": _yaml("mock_apis/api_two.openapi.yaml"),
}

_PETSTORE_SPEC = _yaml("petstore/petstore.openapi.yaml")
PETSTORE_SOURCE_DESCRIPTIONS = {"petstore": _PETSTORE_SPEC}

_USERS_SPEC = _yaml("mock_apis/users.openapi.yaml")
MULTI_SOURCE_DESCRIPTIONS = {
    "petstore": _PETSTORE_SPEC,
    "users": _USERS_SPEC,
}


def make_finder_with_sources(source_descriptions):
    return OperationFinder(source_descriptions)


def test_extract_security_requirements_path_level_override():
    source_descriptions = {
        "api": {
            "security": [{"apiKey": []}],
            "paths": {
                "/public/resource": {
                    "security": [],
                    "get": {"responses": {"200": {"description": "ok"}}},
                },
                "/private/resource": {"get": {"responses": {"200": {"description": "ok"}}}},
            },
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"}
                }
            },
        }
    }
    finder = make_finder_with_sources(source_descriptions)

    operation_info = {
        "operation": source_descriptions["api"]["paths"]["/public/resource"]["get"],
        "source": "api",
        "path": "/public/resource",
    }
    result = finder.extract_security_requirements(operation_info)
    assert (
        result == []
    ), "Path-level security override (empty array) should disable security requirements"

    operation_info_private = {
        "operation": source_descriptions["api"]["paths"]["/private/resource"]["get"],
        "source": "api",
        "path": "/private/resource",
    }
    result_private = finder.extract_security_requirements(operation_info_private)
    assert result_private == [
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
    ], "Should inherit global security when no path-level override is present"


def test_extract_security_requirements_operation_level():
    source_descriptions = {
        "api": {
            "security": [{"apiKey": []}],
            "paths": {
                "/resource": {
                    "get": {
                        "security": [{"oauth2": ["read"]}],
                        "responses": {"200": {"description": "ok"}},
                    },
                    "post": {"responses": {"200": {"description": "ok"}}},
                }
            },
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"},
                    "oauth2": {
                        "type": "oauth2",
                        "flows": {
                            "implicit": {
                                "authorizationUrl": "https://example.com",
                                "scopes": {"read": "Read access"},
                            }
                        },
                    },
                }
            },
        }
    }
    finder = make_finder_with_sources(source_descriptions)

    operation_info_op = {
        "operation": source_descriptions["api"]["paths"]["/resource"]["get"],
        "source": "api",
        "path": "/resource",
    }
    result_op = finder.extract_security_requirements(operation_info_op)
    assert result_op == [
        SecurityOption(requirements=[SecurityRequirement(scheme_name="oauth2", scopes=["read"])])
    ], "Operation-level security should take precedence and match oauth2 scheme"


def test_extract_security_requirements_global_level():
    source_descriptions = {
        "api": {
            "security": [{"apiKey": []}],
            "paths": {"/resource": {"post": {"responses": {"200": {"description": "ok"}}}}},
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"}
                }
            },
        }
    }
    finder = make_finder_with_sources(source_descriptions)

    operation_info_global = {
        "operation": source_descriptions["api"]["paths"]["/resource"]["post"],
        "source": "api",
        "path": "/resource",
    }
    result_global = finder.extract_security_requirements(operation_info_global)
    assert result_global == [
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
    ], "Global security should apply and match apiKey scheme"


class TestOperationFinderHttpPath(unittest.TestCase):

    def setUp(self):
        """Set up the test case with OperationFinder instance."""
        self.finder = OperationFinder(MOCK_SOURCE_DESC)

    def test_find_exact_path_and_method_success(self):
        """Test finding an operation with exact path and method match."""
        result = self.finder.find_by_http_path_and_method("/users", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["path"], "/users")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operationId"], "listUsers")
        self.assertEqual(result["url"], "http://localhost/users")

    def test_find_template_path_and_method_success(self):
        """Test finding an operation with a template path and method match."""
        # Note: Current implementation uses simple segment check, might need adjustment
        result = self.finder.find_by_http_path_and_method("/users/123", "DELETE")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["path"], "/users/{userId}")  # Should return template path
        self.assertEqual(result["method"], "delete")
        self.assertEqual(result["operationId"], "deleteUser")
        self.assertEqual(result["url"], "http://localhost/users/{userId}")

    def test_find_case_insensitive_method_success(self):
        """Test finding an operation with a case-insensitive method match."""
        result = self.finder.find_by_http_path_and_method("/users", "post")  # Lowercase 'post'
        self.assertIsNotNone(result)
        self.assertEqual(result["method"], "post")
        self.assertEqual(result["operationId"], "createUser")

    def test_find_path_exists_method_missing(self):
        """Test finding when path exists but the requested method does not."""
        result = self.finder.find_by_http_path_and_method("/users", "PUT")
        self.assertIsNone(result)

    def test_find_path_missing(self):
        """Test finding when the requested path does not exist."""
        result = self.finder.find_by_http_path_and_method("/nonexistent", "GET")
        self.assertIsNone(result)

    def test_find_in_second_api_source(self):
        """Test finding an operation defined in the second API source."""
        result = self.finder.find_by_http_path_and_method("/items", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_two")
        self.assertEqual(result["path"], "/items")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operationId"], "listItems")
        self.assertEqual(result["url"], "http://localhost:8080/items")


def test_get_security_requirements_for_workflow_basic():
    arazzo_spec = {"workflows": [{"workflowId": "wf1", "steps": [{"operationId": "op1"}]}]}
    source_descriptions = {
        "src": {
            "servers": [{"url": "http://dummy.com"}],
            "paths": {"/foo": {"get": {"operationId": "op1", "security": [{"apiKey": []}]}}},
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}},
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow(
        "wf1", arazzo_spec, source_descriptions
    )
    assert list(result.keys()) == ["src"]
    assert result["src"] == [
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
    ]


def test_get_security_requirements_for_workflow_multiple_sources():
    arazzo_spec = {
        "workflows": [
            {"workflowId": "wf2", "steps": [{"operationId": "op1"}, {"operationId": "op2"}]}
        ]
    }
    source_descriptions = {
        "src1": {
            "servers": [{"url": "http://dummy1.com"}],
            "paths": {"/foo": {"get": {"operationId": "op1", "security": [{"apiKey": []}]}}},
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}},
        },
        "src2": {
            "servers": [{"url": "http://dummy2.com"}],
            "paths": {"/bar": {"post": {"operationId": "op2", "security": [{"oauth2": ["read"]}]}}},
            "security": [{"oauth2": ["read"]}],
            "components": {"securitySchemes": {"oauth2": {"type": "oauth2"}}},
        },
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow(
        "wf2", arazzo_spec, source_descriptions
    )
    assert set(result.keys()) == {"src1", "src2"}
    assert (
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
        in result["src1"]
    )
    assert (
        SecurityOption(requirements=[SecurityRequirement(scheme_name="oauth2", scopes=["read"])])
        in result["src2"]
    )
    assert len(result["src1"]) == 1
    assert len(result["src2"]) == 1


def test_get_security_requirements_for_workflow_deduplication():
    arazzo_spec = {
        "workflows": [
            {"workflowId": "wf3", "steps": [{"operationId": "op1"}, {"operationId": "op2"}]}
        ]
    }
    source_descriptions = {
        "src": {
            "servers": [{"url": "http://dummy.com"}],
            "paths": {
                "/foo": {"get": {"operationId": "op1", "security": [{"apiKey": []}]}},
                "/bar": {"post": {"operationId": "op2", "security": [{"apiKey": []}]}},
            },
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}},
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow(
        "wf3", arazzo_spec, source_descriptions
    )
    assert list(result.keys()) == ["src"]
    assert result["src"] == [
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
    ]


def test_get_security_requirements_for_workflow_duplicate_names_different_sources():
    arazzo_spec = {
        "workflows": [
            {"workflowId": "wf4", "steps": [{"operationId": "op1"}, {"operationId": "op2"}]}
        ]
    }
    source_descriptions = {
        "src1": {
            "servers": [{"url": "http://dummy1.com"}],
            "paths": {"/foo": {"get": {"operationId": "op1", "security": [{"apiKey": []}]}}},
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey", "x-issuer": "src1"}}},
        },
        "src2": {
            "servers": [{"url": "http://dummy2.com"}],
            "paths": {
                "/bar": {
                    "post": {
                        "operationId": "op2",
                        "security": [{"apiKey": []}],  # Same scheme name, different source
                    }
                }
            },
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey", "x-issuer": "src2"}}},
        },
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow(
        "wf4", arazzo_spec, source_descriptions
    )
    assert set(result.keys()) == {"src1", "src2"}
    assert (
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
        in result["src1"]
    )
    assert (
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
        in result["src2"]
    )
    assert len(result["src1"]) == 1
    assert len(result["src2"]) == 1


def test_get_security_requirements_for_workflow_scope_merging():
    """
    If two operations in the same workflow have SecurityOptions with the same scheme name but different scopes,
    the merged SecurityOption should contain all unique scopes for that scheme.
    """
    arazzo_spec = {
        "workflows": [
            {
                "workflowId": "wf_scope_merge",
                "steps": [{"operationId": "op1"}, {"operationId": "op2"}],
            }
        ]
    }
    source_descriptions = {
        "src": {
            "servers": [{"url": "http://dummy.com"}],
            "paths": {
                "/foo": {"get": {"operationId": "op1", "security": [{"oauth2": ["read"]}]}},
                "/bar": {"post": {"operationId": "op2", "security": [{"oauth2": ["write"]}]}},
            },
            "security": [{"oauth2": ["read", "write"]}],
            "components": {"securitySchemes": {"oauth2": {"type": "oauth2"}}},
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow(
        "wf_scope_merge", arazzo_spec, source_descriptions
    )
    assert list(result.keys()) == ["src"]
    # Allow for scopes to be in any order
    assert len(result["src"]) == 1
    req = result["src"][0].requirements[0]
    assert req.scheme_name == "oauth2"
    assert set(req.scopes) == {"read", "write"}


def test_get_security_requirements_for_openapi_operation_basic():
    openapi_spec = {
        "servers": [{"url": "http://dummy.com"}],
        "paths": {"/foo": {"get": {"operationId": "op1", "security": [{"apiKey": []}]}}},
        "security": [{"apiKey": []}],
        "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}},
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_openapi_operation(openapi_spec, "get", "/foo")
    assert result == [
        SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])
    ]


# ---------------------------------------------------------------------------
# Tests for find_by_path – JSON Pointer (~1) decoding
# ---------------------------------------------------------------------------


class TestFindByPathJsonPointerDecoding(unittest.TestCase):
    """
    Tests for OperationFinder.find_by_path covering ~1-encoded JSON Pointer paths.

    The key regression: decoding ~1pets~1{petId} must yield /pets/{petId}, not
    //pets/{petId} (double-slash).  All three internal strategies
    (_extract_path_method_with_regex, _resolve_with_jsonpointer,
    _handle_special_cases) had this bug.
    """

    def setUp(self):
        self.finder = OperationFinder(PETSTORE_SOURCE_DESCRIPTIONS)

    # ------------------------------------------------------------------
    # Simple (non-parameterised) path
    # ------------------------------------------------------------------

    def test_simple_path_by_name(self):
        """Pointer /paths/~1pets/get found when source is looked up by name."""
        result = self.finder.find_by_path("petstore", "/paths/~1pets/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["url"], "https://petstore.example.com/v1/pets")
        self.assertEqual(result["operation"]["operationId"], "listPets")

    def test_simple_path_by_url(self):
        """Pointer /paths/~1pets/get found when source is looked up by base URL."""
        result = self.finder.find_by_path("https://petstore.example.com/v1", "/paths/~1pets/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "petstore")
        self.assertEqual(result["path"], "/pets")
        self.assertEqual(result["method"], "get")

    # ------------------------------------------------------------------
    # Parameterised path – the primary regression case
    # ------------------------------------------------------------------

    def test_parameterised_path_by_name(self):
        """~1pets~1{petId} must decode to /pets/{petId}, not //pets/{petId}."""
        result = self.finder.find_by_path("petstore", "/paths/~1pets~1{petId}/get")
        self.assertIsNotNone(
            result, "Operation must be found – double-slash decode bug would return None"
        )
        self.assertEqual(result["path"], "/pets/{petId}")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["url"], "https://petstore.example.com/v1/pets/{petId}")
        self.assertEqual(result["operation"]["operationId"], "showPetById")

    def test_parameterised_path_by_url(self):
        """Same regression test via URL-based source lookup (full Arazzo operationPath pattern)."""
        result = self.finder.find_by_path(
            "https://petstore.example.com/v1", "/paths/~1pets~1{petId}/get"
        )
        self.assertIsNotNone(result, "Operation must be found via URL source lookup")
        self.assertEqual(result["path"], "/pets/{petId}")
        self.assertEqual(result["method"], "get")

    def test_full_arazzo_operation_path_expression(self):
        """
        Exercises the full Arazzo operationPath pattern where the source expression
        has not yet been evaluated and still contains the raw expression text.
        step_executor splits on '#' and passes the left side to find_by_path; the
        _find_source_description partial-match logic must still locate the spec.
        """
        # source_url as it arrives from step_executor after splitting on '#'
        arazzo_source_ref = "{$sourceDescriptions.petstore.url}"
        result = self.finder.find_by_path(arazzo_source_ref, "/paths/~1pets~1{petId}/get")
        self.assertIsNotNone(result, "Should find via partial name match in expression text")
        self.assertEqual(result["path"], "/pets/{petId}")

    # ------------------------------------------------------------------
    # Multi-segment path
    # ------------------------------------------------------------------

    def test_multi_segment_parameterised_path(self):
        """Three-segment path /pets/{petId}/tags encodes as ~1pets~1{petId}~1tags."""
        result = self.finder.find_by_path("petstore", "/paths/~1pets~1{petId}~1tags/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets/{petId}/tags")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "listPetTags")

    # ------------------------------------------------------------------
    # Negative cases
    # ------------------------------------------------------------------

    def test_nonexistent_path_returns_none(self):
        """A pointer to a path not in the spec returns None."""
        result = self.finder.find_by_path("petstore", "/paths/~1nonexistent/get")
        self.assertIsNone(result)

    def test_unknown_source_returns_none(self):
        """An unrecognisable source URL returns None."""
        result = self.finder.find_by_path(
            "https://completely-unknown.example.com", "/paths/~1pets/get"
        )
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tests for find_by_http_path_and_method – "METHOD /path" convenience wrapper
# ---------------------------------------------------------------------------


class TestFindByHttpPathAndMethodPetstore(unittest.TestCase):
    """
    Regression tests for find_by_http_path_and_method against the petstore spec.

    This method is the backing lookup used by StepExecutor.execute_operation when
    called with an operation_path like "GET /pets/{petId}".  It does NOT involve
    ~1 JSON Pointer encoding – our decode fix must not break this code path.
    """

    def setUp(self):
        self.finder = OperationFinder(PETSTORE_SOURCE_DESCRIPTIONS)

    def test_simple_get(self):
        """GET /pets resolves to listPets."""
        result = self.finder.find_by_http_path_and_method("/pets", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "listPets")
        self.assertEqual(result["url"], "https://petstore.example.com/v1/pets")

    def test_parameterised_get(self):
        """GET /pets/{petId} resolves to showPetById via the template path."""
        result = self.finder.find_by_http_path_and_method("/pets/{petId}", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets/{petId}")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "showPetById")
        self.assertEqual(result["url"], "https://petstore.example.com/v1/pets/{petId}")

    def test_concrete_parameterised_get(self):
        """GET /pets/42 matches the /pets/{petId} template (concrete value)."""
        result = self.finder.find_by_http_path_and_method("/pets/42", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets/{petId}")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "showPetById")

    def test_multi_segment_parameterised_get(self):
        """GET /pets/{petId}/tags matches the three-segment template."""
        result = self.finder.find_by_http_path_and_method("/pets/{petId}/tags", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets/{petId}/tags")
        self.assertEqual(result["operation"]["operationId"], "listPetTags")

    def test_case_insensitive_method(self):
        """Method lookup is case-insensitive."""
        result = self.finder.find_by_http_path_and_method("/pets", "get")
        self.assertIsNotNone(result)
        self.assertEqual(result["method"], "get")

    def test_unknown_path_returns_none(self):
        result = self.finder.find_by_http_path_and_method("/nonexistent", "GET")
        self.assertIsNone(result)

    def test_wrong_method_returns_none(self):
        """GET /pets exists but DELETE /pets does not."""
        result = self.finder.find_by_http_path_and_method("/pets", "DELETE")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tests for find_by_path – multiple source descriptions registered simultaneously
# ---------------------------------------------------------------------------


class TestOperationFinderWithTwoSources(unittest.TestCase):
    """
    Unit tests for OperationFinder.find_by_path when two distinct source
    descriptions are registered.  Verifies correct source routing and
    ~1-decoding for both the petstore and users specs.
    """

    def setUp(self):
        self.finder = OperationFinder(MULTI_SOURCE_DESCRIPTIONS)

    # --- routing by source name ---

    def test_simple_path_routes_to_petstore(self):
        """A plain path pointer resolves against the petstore spec."""
        result = self.finder.find_by_path("petstore", "/paths/~1pets/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"]["operationId"], "listPets")
        self.assertIn("petstore.example.com", result["url"])

    def test_simple_path_routes_to_users(self):
        """A plain path pointer resolves against the users spec."""
        result = self.finder.find_by_path("users", "/paths/~1users/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"]["operationId"], "listUsers")
        self.assertIn("users.example.com", result["url"])

    def test_petstore_path_not_found_in_users(self):
        """/pets is a petstore path — it must not resolve when users is targeted."""
        result = self.finder.find_by_path("users", "/paths/~1pets/get")
        self.assertIsNone(result)

    def test_users_path_not_found_in_petstore(self):
        """/users is a users path — it must not resolve when petstore is targeted."""
        result = self.finder.find_by_path("petstore", "/paths/~1users/get")
        self.assertIsNone(result)

    # --- ~1 decoding for parameterised paths in each source ---

    def test_tilde_encoded_parameterised_path_petstore(self):
        """~1pets~1{petId} decodes to /pets/{petId} in the petstore spec."""
        result = self.finder.find_by_path("petstore", "/paths/~1pets~1{petId}/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets/{petId}")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "showPetById")

    def test_tilde_encoded_parameterised_path_users(self):
        """~1users~1{userId} decodes to /users/{userId} in the users spec."""
        result = self.finder.find_by_path("users", "/paths/~1users~1{userId}/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/users/{userId}")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "getUserById")

    # --- full Arazzo runtime-expression format ---

    def test_full_arazzo_expression_petstore_simple(self):
        """{$sourceDescriptions.petstore.url}#/paths/~1pets/get resolves correctly."""
        result = self.finder.find_by_path("{$sourceDescriptions.petstore.url}", "/paths/~1pets/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"]["operationId"], "listPets")
        self.assertIn("petstore.example.com", result["url"])

    def test_full_arazzo_expression_petstore_parameterised(self):
        """
        The exact pattern from demo.py step 2:
        {$sourceDescriptions.petstore.url}#/paths/~1pets~1{petId}/get
        must decode ~1pets~1{petId} to /pets/{petId} in the petstore spec.
        """
        result = self.finder.find_by_path(
            "{$sourceDescriptions.petstore.url}", "/paths/~1pets~1{petId}/get"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/pets/{petId}")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "showPetById")
        self.assertIn("petstore.example.com", result["url"])

    def test_full_arazzo_expression_users_simple(self):
        """{$sourceDescriptions.users.url}#/paths/~1users/get resolves correctly."""
        result = self.finder.find_by_path("{$sourceDescriptions.users.url}", "/paths/~1users/get")
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"]["operationId"], "listUsers")
        self.assertIn("users.example.com", result["url"])

    def test_full_arazzo_expression_users_parameterised(self):
        """{$sourceDescriptions.users.url}#/paths/~1users~1{userId}/get decodes correctly."""
        result = self.finder.find_by_path(
            "{$sourceDescriptions.users.url}", "/paths/~1users~1{userId}/get"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/users/{userId}")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operation"]["operationId"], "getUserById")
        self.assertIn("users.example.com", result["url"])

    def test_full_arazzo_expression_cross_source_isolation(self):
        """
        Mismatched expression + path must return None.
        The petstore expression must not accidentally resolve a users path.
        """
        result = self.finder.find_by_path(
            "{$sourceDescriptions.petstore.url}", "/paths/~1users~1{userId}/get"
        )
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tests for find_by_id
# ---------------------------------------------------------------------------


class TestFindById(unittest.TestCase):
    """
    Unit tests for OperationFinder.find_by_id.

    Ensures that plain operationId-based step dispatch still works correctly
    after the ~1 decode fix (which only touched find_by_path internals).
    """

    def setUp(self):
        # api_one: listUsers (GET /users), createUser (POST /users),
        #          getUserById (GET /users/{userId}), deleteUser (DELETE /users/{userId})
        # api_two: listItems (GET /items)
        self.finder = OperationFinder(MOCK_SOURCE_DESC)

    # --- happy-path lookups ---

    def test_find_get_operation_returns_correct_fields(self):
        """find_by_id returns source, path, method, url, and operation dict."""
        result = self.finder.find_by_id("listUsers")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["path"], "/users")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["url"], "http://localhost/users")
        self.assertIsNotNone(result.get("operation"))

    def test_find_post_operation(self):
        """find_by_id locates a POST operation, not just GET."""
        result = self.finder.find_by_id("createUser")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["method"], "post")
        self.assertEqual(result["path"], "/users")

    def test_find_delete_operation(self):
        """find_by_id locates a DELETE operation on a parameterised path."""
        result = self.finder.find_by_id("deleteUser")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["method"], "delete")
        self.assertEqual(result["path"], "/users/{userId}")
        self.assertEqual(result["url"], "http://localhost/users/{userId}")

    def test_find_operation_in_second_source(self):
        """find_by_id searches all registered sources, not just the first."""
        result = self.finder.find_by_id("listItems")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_two")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["path"], "/items")
        self.assertEqual(result["url"], "http://localhost:8080/items")

    def test_find_parameterised_path_url(self):
        """Base URL is correctly prepended even for parameterised path templates."""
        result = self.finder.find_by_id("getUserById")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/users/{userId}")
        self.assertEqual(result["url"], "http://localhost/users/{userId}")

    # --- negative cases ---

    def test_nonexistent_operation_returns_none(self):
        """An operationId that appears in no source returns None."""
        result = self.finder.find_by_id("completelyMadeUpOperation")
        self.assertIsNone(result)

    def test_empty_operation_id_returns_none(self):
        """An empty string operationId returns None."""
        result = self.finder.find_by_id("")
        self.assertIsNone(result)


class TestFindByPathSourceNameForSecurityResolution(unittest.TestCase):
    """
    Regression tests ensuring that find_by_path sets operation_info["source"]
    to the actual source_descriptions dict key, NOT the raw URL/expression.

    This is critical because extract_security_requirements() uses
    ``source_name in self.source_descriptions`` to look up path-level and
    global security requirements. When source was incorrectly set to a URL,
    that lookup silently failed and requests went out unauthenticated.
    """

    def setUp(self):
        self.source_descriptions = {
            "discord": {
                "servers": [{"url": "https://discord.com/api/v10"}],
                "security": [{"BotToken": []}],
                "paths": {
                    "/channels/{channel_id}/messages": {
                        "post": {
                            "operationId": "sendMessage",
                            "responses": {"200": {"description": "ok"}},
                        }
                    }
                },
                "components": {
                    "securitySchemes": {"BotToken": {"type": "http", "scheme": "bearer"}}
                },
            }
        }
        self.finder = OperationFinder(self.source_descriptions)

    def test_url_lookup_returns_dict_key_as_source(self):
        """When source_url is the server URL, source must be the dict key."""
        result = self.finder.find_by_path(
            "https://discord.com/api/v10",
            "/paths/~1channels~1{channel_id}~1messages/post",
        )
        self.assertIsNotNone(result)
        self.assertEqual(
            result["source"],
            "discord",
            "source must be the dict key, not the URL",
        )

    def test_security_requirements_found_after_url_lookup(self):
        """
        End-to-end: find_by_path with a URL, then extract_security_requirements
        must find the global security requirements (not return empty).
        """
        op_info = self.finder.find_by_path(
            "https://discord.com/api/v10",
            "/paths/~1channels~1{channel_id}~1messages/post",
        )
        self.assertIsNotNone(op_info)
        security_options = self.finder.extract_security_requirements(op_info)
        self.assertEqual(len(security_options), 1)
        self.assertEqual(security_options[0].requirements[0].scheme_name, "BotToken")

    def test_expression_lookup_returns_dict_key_as_source(self):
        """When source_url is an Arazzo expression, source must be the dict key."""
        result = self.finder.find_by_path(
            "{$sourceDescriptions.discord.url}",
            "/paths/~1channels~1{channel_id}~1messages/post",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "discord")

    def test_security_requirements_found_after_expression_lookup(self):
        """
        End-to-end: find_by_path with an Arazzo expression, then
        extract_security_requirements must find global security.
        """
        op_info = self.finder.find_by_path(
            "{$sourceDescriptions.discord.url}",
            "/paths/~1channels~1{channel_id}~1messages/post",
        )
        self.assertIsNotNone(op_info)
        security_options = self.finder.extract_security_requirements(op_info)
        self.assertEqual(len(security_options), 1)
        self.assertEqual(security_options[0].requirements[0].scheme_name, "BotToken")


if __name__ == "__main__":
    unittest.main()
