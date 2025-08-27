import json

from arazzo_generator.llm.litellm_service import LiteLLMService


class TestLLMServiceFormatEndpoints:
    # Tests endpoint formatting for minimal endpoint
    def test_format_endpoints_for_llm_minimal(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"
        assert svc.llm_model == "gemini/gemini-2.0-flash"

        endpoints = {
            "/pets": {
                "get": {
                    "operation_id": "listPets",
                    "summary": "List pets",
                    "description": "Returns all pets",
                    "parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                        {"$ref": "#/components/parameters/offset"},
                    ],
                    "request_body": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "A paged array of pets",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Pets"}
                                }
                            },
                        },
                        "default": {"$ref": "#/components/responses/Error"},
                    },
                    "tags": ["pets"],
                }
            }
        }
        json_str = svc._format_endpoints_for_llm(endpoints)
        formatted = json.loads(json_str)
        assert isinstance(formatted, list)
        # Check that parameters and refs are preserved
        params = formatted[0]["parameters"]
        assert any("$ref" in p for p in params)
        # Check request_body schema ref
        req_body = formatted[0]["request_body"]
        assert "content" in req_body
        assert "application/json" in req_body["content"]
        assert (
            req_body["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/Pet"
        )
        # Check responses
        responses = formatted[0]["responses"]
        assert "200" in responses
        assert "content" in responses["200"]
        assert "application/json" in responses["200"]["content"]
        assert (
            responses["200"]["content"]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/Pets"
        )
        assert "default" in responses
        assert "$ref" in responses["default"]
        assert responses["default"]["$ref"] == "#/components/responses/Error"

    # Tests endpoint formatting for endpoints with only ref parameters
    def test_format_endpoints_for_llm_only_ref_parameters(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {
            "/foo": {
                "get": {
                    "parameters": [
                        {"$ref": "#/components/parameters/FooParam"},
                        {"$ref": "#/components/parameters/BarParam"},
                    ],
                    "responses": {},
                }
            }
        }
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        assert all("$ref" in p for p in formatted[0]["parameters"])

    # Tests endpoint formatting for endpoints with nonref parameters with nested schema ref
    def test_format_endpoints_for_llm_nonref_param_with_nested_schema_ref(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {
            "/bar": {
                "post": {
                    "parameters": [
                        {
                            "name": "foo",
                            "in": "query",
                            "schema": {"$ref": "#/components/schemas/Foo"},
                        }
                    ],
                    "responses": {},
                }
            }
        }
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        assert formatted[0]["parameters"][0]["schema"] == {"$ref": "#/components/schemas/Foo"}

    # Tests endpoint formatting for endpoints with request body as ref
    def test_format_endpoints_for_llm_request_body_as_ref(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {
            "/baz": {
                "put": {
                    "request_body": {"$ref": "#/components/requestBodies/Baz"},
                    "responses": {},
                }
            }
        }
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        assert formatted[0]["request_body"] == {"$ref": "#/components/requestBodies/Baz"}

    # Tests endpoint formatting for endpoints with no parameters or request body
    def test_format_endpoints_for_llm_no_parameters_or_request_body(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {"/empty": {"get": {"responses": {"200": {"description": "ok"}}}}}
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        assert formatted[0]["parameters"] == []
        assert formatted[0]["request_body"] == {}

    # Tests endpoint formatting for endpoints with non-JSON content type
    def test_format_endpoints_for_llm_nonjson_content_type_only(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {
            "/upload": {
                "post": {
                    "request_body": {
                        "content": {"multipart/form-data": {"schema": {"type": "string"}}}
                    },
                    "responses": {},
                }
            }
        }
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        # Should include the first available content type
        assert "multipart/form-data" in formatted[0]["request_body"]["content"]

    # Tests endpoint formatting for endpoints with empty content types
    def test_format_endpoints_for_llm_empty_content_types(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {"/emptycontent": {"post": {"request_body": {"content": {}}, "responses": {}}}}
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        # No content types, so content should be empty
        assert formatted[0]["request_body"]["content"] == {}

    # Tests endpoint formatting for endpoints with JSON and non-JSON content types
    def test_format_endpoints_for_llm_json_and_nonjson_content_types(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {
            "/pets": {
                "get": {
                    "operation_id": "listPets",
                    "request_body": {
                        "content": {
                            "application/json": {"schema": {"type": "object"}},
                            "text/plain": {"schema": {"type": "string"}},
                        }
                    },
                    "responses": {},
                }
            }
        }
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        # Should prefer JSON content type
        assert "application/json" in formatted[0]["request_body"]["content"]
        assert formatted[0]["path"] == "/pets"
        assert formatted[0]["method"] == "get"
        assert formatted[0]["operation_id"] == "listPets"

    # Tests endpoint formatting for endpoints with deeply nested parameters
    def test_format_endpoints_for_llm_deep_nesting(self):
        svc = LiteLLMService(api_key="test-key")
        endpoints = {
            "/nested": {
                "post": {
                    "parameters": [
                        {
                            "name": "deep",
                            "in": "body",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "level1": {
                                        "type": "object",
                                        "properties": {
                                            "level2": {
                                                "type": "object",
                                                "properties": {
                                                    "level3": {
                                                        "$ref": "#/components/schemas/DeepNested"
                                                    }
                                                },
                                            }
                                        },
                                    }
                                },
                            },
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        }
        formatted = json.loads(svc._format_endpoints_for_llm(endpoints))
        assert "properties" in formatted[0]["parameters"][0]["schema"]
        assert "level1" in formatted[0]["parameters"][0]["schema"]["properties"]
        assert (
            "level2"
            in formatted[0]["parameters"][0]["schema"]["properties"]["level1"]["properties"]
        )
        assert (
            "level3"
            in formatted[0]["parameters"][0]["schema"]["properties"]["level1"]["properties"][
                "level2"
            ]["properties"]
        )
        assert (
            "$ref"
            in formatted[0]["parameters"][0]["schema"]["properties"]["level1"]["properties"][
                "level2"
            ]["properties"]["level3"]
        )
        assert (
            formatted[0]["parameters"][0]["schema"]["properties"]["level1"]["properties"]["level2"][
                "properties"
            ]["level3"]["$ref"]
            == "#/components/schemas/DeepNested"
        )
