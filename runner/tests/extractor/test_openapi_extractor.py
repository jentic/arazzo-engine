#!/usr/bin/env python3
"""
Tests for the OpenAPI Extractor module.
"""

import logging
import sys

import pytest

from arazzo_runner.extractor.openapi_extractor import (
    _limit_dict_depth,
    _resolve_schema_refs,
    extract_operation_io,
    resolve_schema,
)

# Configure specific logger for the extractor module for debug output
extractor_logger = logging.getLogger("arazzo_runner.extractor.openapi_extractor")
extractor_logger.setLevel(logging.DEBUG)
# Ensure handler exists to output to stderr
if not extractor_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    handler.setFormatter(formatter)
    extractor_logger.addHandler(handler)

# Example spec from task.md (simplified slightly for testing focus)
TEST_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "servers": [{"url": "http://test.com/api"}],
    "paths": {
        "/orders": {
            "post": {
                "summary": "Create a new order",
                "operationId": "createOrder",
                "parameters": [
                    {
                        "name": "X-Request-ID",
                        "in": "header",
                        "required": False,
                        "description": "Request identifier for tracing",
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {"$ref": "#/components/requestBodies/OrderRequest"},
                "responses": {
                    "201": {"$ref": "#/components/responses/OrderCreated"},
                    "400": {"description": "Invalid input"},
                },
                "security": [
                    {"apiKeyAuth": []},
                    {"oauth2_def": ["write:orders"]},
                    {"basicAuth": [], "petstore_auth": ["read:pets", "write:pets"]},
                ],
            }
        }
    },
    "components": {
        "schemas": {
            "Order": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "items": {"type": "array", "items": {"$ref": "#/components/schemas/OrderItem"}},
                    "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]},
                },
                "required": ["items"],
            },
            "OrderInput": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": {"$ref": "#/components/schemas/OrderItem"}},
                    "customer_notes": {
                        "type": "string",
                        "description": "Additional notes from the customer",
                    },
                },
            },
            "OrderItem": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer"},
                },
                "required": ["product_id", "quantity"],
            },
        },
        "requestBodies": {
            "OrderRequest": {
                "description": "Order details",
                "required": True,
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/OrderInput"}}
                },
            }
        },
        "responses": {
            "OrderCreated": {
                "description": "Order created successfully",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Order"}}},
            }
        },
        "securitySchemes": {
            "oauth2_def": {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": "http://test.com/oauth/token",
                        "scopes": {
                            "write:orders": "modify orders in your account",
                            "read:orders": "read your orders",
                        },
                    }
                },
            },
            "apiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-KEY"},
            "basicAuth": {"type": "http", "scheme": "basic"},
            "petstore_auth": {
                "type": "oauth2",
                "flows": {
                    "implicit": {
                        "authorizationUrl": "http://example.org/api/oauth/dialog",
                        "scopes": {
                            "write:pets": "modify pets in your account",
                            "read:pets": "read your pets",
                        },
                    }
                },
            },
        },
    },
}


def test_extract_order_post_details():
    """
    Tests extracting details for the POST /orders operation.
    """
    extracted = extract_operation_io(TEST_SPEC, "/orders", "post")

    # --- Assert Inputs (OpenAPI object structure) ---
    assert "inputs" in extracted
    assert isinstance(extracted["inputs"], dict)
    assert extracted["inputs"].get("type") == "object"
    assert "properties" in extracted["inputs"]
    assert isinstance(extracted["inputs"]["properties"], dict)

    input_properties = extracted["inputs"]["properties"]

    # Check non-body parameter (simplified schema within properties)
    assert "X-Request-ID" in input_properties
    # Check type, description, and schema. Required status is in the top-level list.
    expected_param_details = {
        "type": "string",
        "description": "Request identifier for tracing",
        "schema": {"type": "string", "format": "uuid"},
    }
    assert input_properties["X-Request-ID"] == expected_param_details
    # Check that it's NOT required in the top-level list
    assert "X-Request-ID" not in extracted["inputs"].get("required", [])

    # Check the flattened 'items' property from the body
    assert "items" in input_properties
    # Manually construct expected resolved items schema
    expected_items_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "product_id": {"type": "string"},
                "quantity": {"type": "integer"},
            },
            "required": ["product_id", "quantity"],
        },
    }
    assert input_properties["items"] == expected_items_schema

    # Check the flattened 'customer_notes' property from the body
    assert "customer_notes" in input_properties
    assert input_properties["customer_notes"] == {
        "type": "string",
        "description": "Additional notes from the customer",
    }

    # Check required properties from the body are in the top-level required list
    # 'items' is NOT listed in the requestBody schema's top-level required list in TEST_SPEC
    assert "items" not in extracted["inputs"].get("required", [])
    # customer_notes was not required in the body schema
    assert "customer_notes" not in extracted["inputs"].get("required", [])

    # --- Assert Outputs (Full schema) ---
    assert "outputs" in extracted
    # Manually construct expected resolved Order schema
    expected_resolved_output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "product_id": {"type": "string"},
                        "quantity": {"type": "integer"},
                    },
                    "required": ["product_id", "quantity"],
                },
            },
            "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]},
        },
        "required": ["items"],  # Add missing required field
    }
    assert extracted["outputs"] == expected_resolved_output_schema

    # --- Assert Security Requirements ---
    assert "security_requirements" in extracted
    expected_security_req = [
        {"apiKeyAuth": []},
        {"oauth2_def": ["write:orders"]},
        {"basicAuth": [], "petstore_auth": ["read:pets", "write:pets"]},
    ]
    assert extracted["security_requirements"] == expected_security_req

    # --- Assert No Other Top-Level Keys (like old 'parameters', 'request_body', 'responses') ---
    assert all(key in ["inputs", "outputs", "security_requirements"] for key in extracted.keys())


@pytest.mark.parametrize(
    "data, max_depth, expected",
    [
        # Basic dict limiting
        ({"a": {"b": {"c": 1}}}, 0, "object"),
        (
            {"a": {"b": {"c": 1, "type": "nested_object"}}},
            0,
            "object",
        ),  # Corrected expectation for max_depth=0
        ({"a": {"b": {"c": 1}}}, 1, {"a": "object"}),
        ({"a": {"b": {"c": 1}}}, 2, {"a": {"b": "object"}}),
        ({"a": {"b": {"c": 1}}}, 3, {"a": {"b": {"c": 1}}}),
        ({"a": {"b": {"c": 1}}}, 4, {"a": {"b": {"c": 1}}}),  # Depth greater than actual
        # Basic list limiting
        ([[["a"]]], 0, "array"),
        ([[["a"]]], 1, ["array"]),
        ([[["a"]]], 2, [["array"]]),
        ([[["a"]]], 3, [[["a"]]]),
        ([[["a"]]], 4, [[["a"]]]),
        # Mixed dict/list limiting
        ({"a": [1, {"b": [2, 3]}]}, 0, "object"),
        ({"a": [1, {"b": [2, 3]}]}, 1, {"a": "array"}),
        ({"a": [1, {"b": [2, 3]}]}, 2, {"a": [1, "object"]}),
        ({"a": [1, {"b": [2, 3]}]}, 3, {"a": [1, {"b": "array"}]}),
        ({"a": [1, {"b": [2, 3]}]}, 4, {"a": [1, {"b": [2, 3]}]}),
        # Other types
        ("string", 1, "string"),
        (123, 1, 123),
        (True, 1, True),
        (None, 1, None),
        ({}, 1, {}),  # Empty dict
        ([], 1, []),  # Empty list
    ],
)
def test_limit_dict_depth(data, max_depth, expected):
    """Tests the _limit_dict_depth function with various inputs and depths."""
    result = _limit_dict_depth(data, max_depth)
    assert result == expected


def test_extracts_implicit_url_param():
    """
    If a path parameter is present in the URL but not declared in the spec, it should still be extracted as required.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/widgets/{widget_id}": {
                "get": {"summary": "Get widget by ID", "responses": {"200": {"description": "ok"}}}
            }
        },
    }
    result = extract_operation_io(spec, "/widgets/{widget_id}", "get")
    props = result["inputs"]["properties"]
    assert "widget_id" in props
    # Path params derived from URL are always required
    assert "widget_id" in result["inputs"].get("required", [])
    # Check the type (defaults to string if not specified)
    assert props["widget_id"] == {"type": "string", "schema": {"type": "string"}}


def test_extracts_explicit_url_param():
    """
    If a path parameter is specified in both the URL and the spec, it should be extracted as required and match the declared type.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/gadgets/{gadget_id}": {
                "get": {
                    "summary": "Get gadget by ID",
                    "parameters": [
                        {
                            "name": "gadget_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    result = extract_operation_io(spec, "/gadgets/{gadget_id}", "get")
    props = result["inputs"]["properties"]
    assert "gadget_id" in props
    # Path params are always required
    assert "gadget_id" in result["inputs"].get("required", [])
    # Check the type matches the spec
    assert props["gadget_id"] == {"type": "integer", "schema": {"type": "integer"}}


def test_extract_operation_io_depth_limits():
    """
    extract_operation_io should respect input_max_depth and output_max_depth for truncating schema depth.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "DepthTest API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/foo/{bar}": {
                "post": {
                    "parameters": [
                        {
                            "name": "bar",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "deep": {
                                            "type": "object",
                                            "properties": {
                                                "deeper": {
                                                    "type": "object",
                                                    "properties": {"val": {"type": "string"}},
                                                }
                                            },
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "arr": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {"x": {"type": "integer"}},
                                                },
                                            }
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }
    # Limit input to 2 levels, output to 1 level
    result = extract_operation_io(spec, "/foo/{bar}", "post", input_max_depth=2, output_max_depth=1)

    # --- Check Input Depth Limit (input_max_depth=2) ---
    assert "inputs" in result
    assert result["inputs"].get("type") == "object"
    input_props = result["inputs"].get("properties", {})

    # Path parameter 'bar' should exist and its value truncated
    assert "bar" in input_props
    # At depth=2, _limit_dict_depth returns the type string for the primitive schema
    assert input_props["bar"] == "string"

    # Body property 'deep' should be flattened and its value truncated
    assert "deep" in input_props
    # At depth=2, _limit_dict_depth returns the type of the nested object
    assert input_props["deep"] == "object"

    # Check required fields
    assert result["inputs"].get("required") == ["bar"]

    # --- Check Output Depth Limit (output_max_depth=1) ---
    assert "outputs" in result
    output_schema = result["outputs"]
    assert output_schema.get("type") == "object"
    # At depth=1, _limit_dict_depth truncates the 'properties' dict to its type
    assert output_schema.get("properties") == "object"


def test_no_params_or_body():
    """
    If an operation has no parameters or body, extract_operation_io should return an empty inputs dict.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/widgets": {
                "get": {"summary": "Get widgets", "responses": {"200": {"description": "ok"}}}
            }
        },
    }
    result = extract_operation_io(spec, "/widgets", "get")
    assert "inputs" in result
    assert result["inputs"] == {"type": "object", "properties": {}, "required": []}


def test_resolve_schema_refs_circular_dependency():
    """Tests that _resolve_schema_refs handles circular dependencies gracefully."""
    circular_spec = {
        "components": {
            "schemas": {
                "SelfReferential": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "child": {"$ref": "#/components/schemas/SelfReferential"},
                    },
                },
                "IndirectA": {
                    "type": "object",
                    "properties": {"link_to_b": {"$ref": "#/components/schemas/IndirectB"}},
                },
                "IndirectB": {
                    "type": "object",
                    "properties": {"link_to_a": {"$ref": "#/components/schemas/IndirectA"}},
                },
            }
        }
    }

    schema_to_resolve_direct = {"$ref": "#/components/schemas/SelfReferential"}
    schema_to_resolve_indirect = {"$ref": "#/components/schemas/IndirectA"}

    # Test direct circular reference
    resolved_direct = _resolve_schema_refs(schema_to_resolve_direct, circular_spec)
    # Expect the recursion to stop and return the $ref at the point of circularity.
    # The 'SelfReferential' schema's 'child' property should still be a $ref to itself.
    assert isinstance(resolved_direct, dict), "Resolved direct schema should be a dict"
    assert resolved_direct.get("type") == "object"
    assert "properties" in resolved_direct
    child_prop = resolved_direct.get("properties", {}).get("child")
    assert isinstance(child_prop, dict), "Child property should be a dict"
    assert (
        child_prop.get("$ref") == "#/components/schemas/SelfReferential"
    ), "Direct circular $ref was not preserved as expected"

    resolved_indirect = _resolve_schema_refs(schema_to_resolve_indirect, circular_spec)
    # Expect the recursion to stop when IndirectB tries to resolve IndirectA again.
    # So, IndirectA -> IndirectB -> $ref to IndirectA
    assert isinstance(
        resolved_indirect, dict
    ), "Resolved indirect schema (IndirectA) should be a dict"
    assert resolved_indirect.get("type") == "object"
    link_to_b_prop = resolved_indirect.get("properties", {}).get("link_to_b")
    assert isinstance(link_to_b_prop, dict), "link_to_b property (IndirectB) should be a dict"
    assert link_to_b_prop.get("type") == "object"
    link_to_a_prop = link_to_b_prop.get("properties", {}).get("link_to_a")
    assert isinstance(link_to_a_prop, dict), "link_to_a property should be a dict"
    assert (
        link_to_a_prop.get("$ref") == "#/components/schemas/IndirectA"
    ), "Indirect circular $ref was not preserved as expected"


def test_resolve_schema_refs_complex_circular_dependency():
    """Tests that _resolve_schema_refs handles complex circular dependencies gracefully."""
    circular_spec = {
        "components": {
            "schemas": {
                # Direct self-reference via array items and allOf
                "SelfReferential": {
                    "type": "object",
                    "description": "base desc",
                    "properties": {
                        "name": {"type": "string"},
                        "children": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/SelfReferential"},
                        },
                    },
                    # include an allOf that references itself to ensure we break cycles within combinators
                    "allOf": [
                        {"$ref": "#/components/schemas/SelfReferential"},
                        {"properties": {"tag": {"type": "string"}}},
                    ],
                },
                # Indirect cycle with sibling overrides and an allOf on B
                "IndirectA": {
                    "type": "object",
                    "properties": {
                        "link_to_b": {"$ref": "#/components/schemas/IndirectB"},
                        "meta": {"type": "object"},
                    },
                },
                "IndirectB": {
                    "type": "object",
                    "properties": {"link_to_a": {"$ref": "#/components/schemas/IndirectA"}},
                    "allOf": [{"properties": {"extra": {"type": "string"}}}],
                },
                # Diamond/cross cycles through oneOf
                "DiamondA": {
                    "type": "object",
                    "properties": {
                        "next": {
                            "oneOf": [
                                {"$ref": "#/components/schemas/DiamondB"},
                                {"$ref": "#/components/schemas/DiamondC"},
                            ]
                        }
                    },
                },
                "DiamondB": {
                    "type": "object",
                    "properties": {"back": {"$ref": "#/components/schemas/DiamondA"}},
                },
                "DiamondC": {
                    "type": "object",
                    "properties": {"back": {"$ref": "#/components/schemas/DiamondA"}},
                },
            }
        }
    }

    schema_self = {"$ref": "#/components/schemas/SelfReferential"}
    schema_indirect = {"$ref": "#/components/schemas/IndirectA"}
    schema_diamond = {"$ref": "#/components/schemas/DiamondA"}

    # Direct self-reference through array items and allOf
    resolved_self = resolve_schema(schema_self, circular_spec)
    assert isinstance(resolved_self, dict)
    assert resolved_self.get("type") == "object"
    # children is an array and items keeps $ref to SelfReferential (cycle preserved)
    children = resolved_self.get("properties", {}).get("children")
    assert isinstance(children, dict) and children.get("type") == "array"
    assert isinstance(children.get("items"), dict)
    assert children.get("items").get("$ref") == "#/components/schemas/SelfReferential"
    # allOf should be merged and removed, with circular references merged as siblings
    assert "allOf" not in resolved_self, "allOf should be merged and removed"

    # Check that circular reference is preserved as a sibling (consistent with regular $ref handling)
    assert "$ref" in resolved_self, "Circular reference should be preserved as sibling"
    assert resolved_self["$ref"] == "#/components/schemas/SelfReferential"

    # Check that properties from non-circular allOf items are merged
    assert "tag" in resolved_self.get(
        "properties", {}
    ), "Tag property from allOf should be merged into main properties"
    assert resolved_self["properties"]["tag"]["type"] == "string"

    # Indirect cycle with allOf on B
    resolved_indirect = resolve_schema(schema_indirect, circular_spec)
    assert isinstance(resolved_indirect, dict)
    assert resolved_indirect.get("type") == "object"
    link_to_b = resolved_indirect.get("properties", {}).get("link_to_b")
    assert isinstance(link_to_b, dict) and link_to_b.get("type") == "object"
    # B should still reference A under link_to_a, preserving the cycle
    link_to_a = link_to_b.get("properties", {}).get("link_to_a")
    assert isinstance(link_to_a, dict)
    assert link_to_a.get("$ref") == "#/components/schemas/IndirectA"
    # allOf on B should be merged and the extra property should be in the main properties
    assert "allOf" not in link_to_b, "allOf should be merged and removed"
    b_properties = link_to_b.get("properties", {})
    assert "extra" in b_properties, "Extra property from allOf should be merged into properties"
    assert b_properties["extra"]["type"] == "string"

    # Diamond cycle via oneOf
    resolved_diamond = resolve_schema(schema_diamond, circular_spec)
    assert isinstance(resolved_diamond, dict)
    oneof = resolved_diamond.get("properties", {}).get("next", {}).get("oneOf")
    assert isinstance(oneof, list)

    # At least one branch should resolve to an object that points back to DiamondA via $ref somewhere
    def branch_points_back(branch: dict) -> bool:
        if not isinstance(branch, dict):
            return False
        # resolved branch may be dict with properties.back as $ref
        back = (
            branch.get("properties", {}).get("back")
            if isinstance(branch.get("properties"), dict)
            else None
        )
        return isinstance(back, dict) and back.get("$ref") == "#/components/schemas/DiamondA"

    assert any(
        branch_points_back(b)
        or (isinstance(b, dict) and b.get("$ref") == "#/components/schemas/DiamondB")
        for b in oneof
    )


def test_resolve_schema_refs_allof_merging():
    """Tests that _resolve_schema_refs properly merges allOf schemas."""
    spec = {
        "components": {
            "schemas": {
                "BaseSchema": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                    "required": ["id"],
                },
                "ExtendedSchema": {
                    "allOf": [
                        {"$ref": "#/components/schemas/BaseSchema"},
                        {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["description"],
                        },
                    ]
                },
            }
        }
    }

    schema = {"$ref": "#/components/schemas/ExtendedSchema"}
    resolved = resolve_schema(schema, spec)

    # allOf should be merged and removed
    assert "allOf" not in resolved

    # Properties from both schemas should be merged
    properties = resolved.get("properties", {})
    assert "id" in properties
    assert "name" in properties
    assert "description" in properties
    assert "tags" in properties

    # Required fields should be merged
    required = resolved.get("required", [])
    assert "id" in required
    assert "description" in required


def test_resolve_schema_refs_allof_with_nested_refs():
    """Tests allOf merging with nested $ref within allOf items."""
    spec = {
        "components": {
            "schemas": {
                "NestedSchema": {
                    "type": "object",
                    "properties": {"nested_prop": {"type": "string"}},
                },
                "AllOfWithNestedRef": {
                    "allOf": [
                        {"type": "object", "properties": {"base_prop": {"type": "string"}}},
                        {
                            "type": "object",
                            "properties": {"nested": {"$ref": "#/components/schemas/NestedSchema"}},
                        },
                    ]
                },
            }
        }
    }

    schema = {"$ref": "#/components/schemas/AllOfWithNestedRef"}
    resolved = resolve_schema(schema, spec)

    # allOf should be merged and removed
    assert "allOf" not in resolved

    # Properties should be merged
    properties = resolved.get("properties", {})
    assert "base_prop" in properties
    assert "nested" in properties

    # Nested $ref should be resolved
    nested = properties.get("nested", {})
    assert isinstance(nested, dict)
    assert "nested_prop" in nested.get("properties", {})


def test_resolve_schema_refs_allof_in_request_body():
    """Tests allOf merging in request body schemas via extract_operation_io."""
    request_body_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/test": {
                "post": {
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "allOf": [
                                        {
                                            "type": "object",
                                            "properties": {"base_field": {"type": "string"}},
                                        },
                                        {
                                            "type": "object",
                                            "properties": {"extended_field": {"type": "integer"}},
                                        },
                                    ]
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    result = extract_operation_io(request_body_spec, "/test", "post")

    # Check that allOf was merged in the input schema
    input_schema = result.get("inputs", {})
    assert "allOf" not in input_schema

    # Check that properties from both allOf items were merged
    properties = input_schema.get("properties", {})
    assert "base_field" in properties
    assert "extended_field" in properties
    assert properties["base_field"]["type"] == "string"
    assert properties["extended_field"]["type"] == "integer"


def test_resolve_schema_refs_allof_with_deep_circular_ref():
    """Tests allOf merging where circular reference is deep in property structure."""
    spec = {
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "address": {
                            "type": "object",
                            "properties": {
                                "street": {"type": "string"},
                                "city": {"type": "string"},
                                "owner": {"$ref": "#/components/schemas/User"},  # Deep circular ref
                            },
                        },
                    },
                    "allOf": [
                        {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "address": {
                                    "type": "object",
                                    "properties": {
                                        "street": {"type": "string"},
                                        "city": {"type": "string"},
                                        "owner": {
                                            "$ref": "#/components/schemas/User"
                                        },  # Deep circular ref
                                    },
                                },
                            },
                        },
                        {
                            "properties": {
                                "phone": {"type": "string"},
                                "age": {"type": "integer"},
                                "preferences": {
                                    "type": "object",
                                    "properties": {
                                        "theme": {"type": "string"},
                                        "notifications": {"type": "boolean"},
                                    },
                                },
                            }
                        },
                    ],
                }
            }
        }
    }

    schema = {"$ref": "#/components/schemas/User"}
    resolved = resolve_schema(schema, spec)

    # allOf should be merged and removed
    assert "allOf" not in resolved

    # Most properties should be merged at the top level
    properties = resolved.get("properties", {})
    assert "name" in properties
    assert "email" in properties
    assert "phone" in properties
    assert "age" in properties
    assert "address" in properties
    assert "preferences" in properties

    # Address should have its properties merged
    address = properties.get("address", {})
    assert isinstance(address, dict)
    address_props = address.get("properties", {})
    assert "street" in address_props
    assert "city" in address_props
    assert "owner" in address_props

    # The circular reference should be preserved deep in the structure
    owner = address_props.get("owner", {})
    assert owner == {"$ref": "#/components/schemas/User"}

    # Preferences should be fully merged
    preferences = properties.get("preferences", {})
    assert isinstance(preferences, dict)
    pref_props = preferences.get("properties", {})
    assert "theme" in pref_props
    assert "notifications" in pref_props

    # No top-level $ref should be added since the circular ref is nested
    assert "$ref" not in resolved


def test_resolve_schema_refs_oneof_behavior():
    """Tests that oneOf is preserved structurally and $refs within it are resolved."""
    spec = {
        "components": {
            "schemas": {
                "BaseSchema": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                },
                "ExtendedSchema": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "SchemaWithOneOf": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "data": {
                            "oneOf": [
                                {"$ref": "#/components/schemas/BaseSchema"},
                                {"$ref": "#/components/schemas/ExtendedSchema"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "custom_field": {"type": "string"},
                                        "nested": {
                                            "oneOf": [
                                                {"$ref": "#/components/schemas/BaseSchema"},
                                                {
                                                    "type": "object",
                                                    "properties": {"other": {"type": "string"}},
                                                },
                                            ]
                                        },
                                    },
                                },
                            ]
                        },
                    },
                },
            }
        }
    }

    schema = {"$ref": "#/components/schemas/SchemaWithOneOf"}
    resolved = resolve_schema(schema, spec)

    # oneOf should be preserved structurally
    data_property = resolved.get("properties", {}).get("data", {})
    assert "oneOf" in data_property, "oneOf should be preserved"

    one_of = data_property["oneOf"]
    assert isinstance(one_of, list), "oneOf should be a list"
    assert len(one_of) == 3, "Should have 3 oneOf options"

    # First option: BaseSchema should be resolved
    first_option = one_of[0]
    assert isinstance(first_option, dict)
    assert "properties" in first_option
    assert "id" in first_option["properties"]
    assert "name" in first_option["properties"]
    assert "$ref" not in first_option, "BaseSchema $ref should be resolved"

    # Second option: ExtendedSchema should be resolved
    second_option = one_of[1]
    assert isinstance(second_option, dict)
    assert "properties" in second_option
    assert "description" in second_option["properties"]
    assert "tags" in second_option["properties"]
    assert "$ref" not in second_option, "ExtendedSchema $ref should be resolved"

    # Third option: Inline object with nested oneOf
    third_option = one_of[2]
    assert isinstance(third_option, dict)
    assert "custom_field" in third_option.get("properties", {})

    # Nested oneOf should also be preserved and resolved
    nested = third_option.get("properties", {}).get("nested", {})
    assert "oneOf" in nested, "Nested oneOf should be preserved"
    nested_one_of = nested["oneOf"]
    assert isinstance(nested_one_of, list)
    assert len(nested_one_of) == 2

    # First nested option should be resolved
    nested_first = nested_one_of[0]
    assert isinstance(nested_first, dict)
    assert "properties" in nested_first
    assert "id" in nested_first["properties"]
    assert "$ref" not in nested_first, "Nested BaseSchema $ref should be resolved"

    # Second nested option should be preserved as-is
    nested_second = nested_one_of[1]
    assert isinstance(nested_second, dict)
    assert "properties" in nested_second
    assert "other" in nested_second["properties"]


def test_merge_json_schemas_boolean_schemas():
    """Test that Boolean JSON Schemas (true/false) are handled correctly."""
    from arazzo_runner.extractor.openapi_extractor import merge_json_schemas

    # Test Boolean schemas
    assert merge_json_schemas(True, {"type": "string"}) is True
    assert merge_json_schemas(False, {"type": "string"}) is False
    assert merge_json_schemas({"type": "string"}, True) is True
    assert merge_json_schemas({"type": "string"}, False) is False
    assert merge_json_schemas(True, True) is True
    assert merge_json_schemas(False, False) is False
    assert merge_json_schemas(True, False) is True  # Target takes precedence

    # Test with allOf folding
    schema_with_boolean = {
        "allOf": [
            True,  # Boolean schema
            {"properties": {"field": {"type": "string"}}},
        ]
    }

    resolved = resolve_schema(schema_with_boolean, {})
    # Should return True since Boolean schemas take precedence
    assert resolved is True
