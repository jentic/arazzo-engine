import json
from unittest.mock import patch

from arazzo_generator.llm.litellm_service import LiteLLMService


class TestPromptBuilder:
    # Tests the build of the endpoint analysis prompt with workflows(optional)
    @patch("arazzo_generator.llm.litellm_service.logger")
    def test_build_endpoint_analysis_prompt_with_workflows(self, mock_logger):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"

        formatted_endpoints = json.dumps(
            [
                {
                    "path": "/users",
                    "method": "GET",
                    "operation_id": "getUsers",
                    "summary": "Retrieve a list of users",
                    "description": "Returns all users in the system.",
                    "parameters": [
                        {"$ref": "#/components/parameters/UsernamePath"},
                        {"$ref": "#/components/parameters/ActivityTypePath"},
                        {"$ref": "#/components/parameters/Limit"},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Activity"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "items": {"$ref": "#/components/schemas/Activity"},
                                        "type": "array",
                                    }
                                }
                            },
                            "description": "An array of activities",
                        },
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden"},
                        "404": {"description": "Not Found"},
                        "500": {"description": "Server Error"},
                    },
                    "tags": ["users"],
                },
                {
                    "path": "/users",
                    "method": "POST",
                    "operation_id": "createUser",
                    "summary": "Create a new user",
                    "description": "Creates a new user.",
                    "parameters": [
                        {"$ref": "#/components/parameters/UsernamePath"},
                        {"$ref": "#/components/parameters/DashboardIDPath"},
                    ],
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {"200": {"description": "Created"}},
                    "tags": ["dashboard"],
                },
            ]
        )

        schemas = {
            "data": {"$ref": "#/components/schemas/Data"},
            "activity": {"$ref": "#/components/schemas/Activity"},
        }

        parameters = [
            {"$ref": "#/components/parameters/UsernamePath"},
            {"$ref": "#/components/parameters/ActivityTypePath"},
            {"$ref": "#/components/parameters/Limit"},
            {"$ref": "#/components/parameters/DashboardIDPath"},
        ]

        responses = {
            "401": {"description": "Unauthorized"},
            "403": {"description": "Forbidden"},
            "404": {"description": "Not Found"},
            "500": {"description": "Server Error"},
            "200": {"description": "Created"},
        }

        request_bodies = {
            "activity": {
                "required": True,
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/Activity"}}
                },
            },
            "content": {"application/json": {}},
        }

        user_workflow_descriptions = ["desc1", "desc2"]

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

        prompt = svc._build_endpoint_analysis_prompt(
            formatted_endpoints=formatted_endpoints,
            schemas=schemas,
            parameters=parameters,
            responses=responses,
            request_bodies=request_bodies,
            metadata=metadata,
            user_workflow_descriptions=user_workflow_descriptions,
        )

        # Test the logging of workflow descriptions being received
        mock_logger.info.assert_called_with("Workflow descriptions received: ['desc1', 'desc2']")

        # Check that the prompt template structure is respected (use key phrases from the template)
        assert "You are an expert API workflow analyst." in prompt
        assert "Please return your answer as a JSON array of workflow definitions" in prompt
        assert "schemas:" in prompt
        assert "parameters:" in prompt
        assert "requestBodies:" in prompt
        assert "responses:" in prompt

        # Check that the prompt contains the endpoints and their details
        # Example Endpoint 1
        assert '"path": "/users"' in prompt
        assert '"method": "GET"' in prompt
        assert '"operation_id": "getUsers"' in prompt
        assert '"summary": "Retrieve a list of users"' in prompt
        assert '"description": "Returns all users in the system."' in prompt
        # Ensure the requestBody structure is present in the prompt
        assert (
            '"requestBody": {' in prompt or '"request_body": {' in prompt
        )  # Accept both camelCase and snake_case
        assert '"required": true' in prompt or '"required": True' in prompt
        assert '"application/json": {' in prompt
        assert '"$ref": "#/components/schemas/Activity"' in prompt
        # 200 with array of activities
        assert '"200": {' in prompt
        assert '"description": "An array of activities"' in prompt
        assert '"type": "array"' in prompt
        assert '"$ref": "#/components/schemas/Activity"' in prompt
        # 401 Unauthorized
        assert '"401": {' in prompt
        assert '"description": "Unauthorized"' in prompt
        # 403 Forbidden
        assert '"403": {' in prompt
        assert '"description": "Forbidden"' in prompt
        # 404 Not Found
        assert '"404": {' in prompt
        assert '"description": "Not Found"' in prompt
        # 500 Server Error
        assert '"500": {' in prompt
        assert '"description": "Server Error"' in prompt

        # Example Endpoint 2
        assert '"path": "/users"' in prompt
        assert '"method": "POST"' in prompt
        assert '"operation_id": "createUser"' in prompt
        assert '"summary": "Create a new user"' in prompt
        assert '"description": "Creates a new user."' in prompt
        # Assert that an empty requestBody with application/json is present for POST /users
        assert (
            '"requestBody": {"content": {"application/json": {}}' in prompt
            or '"request_body": {"content": {"application/json": {}}' in prompt
        )
        # 200 Created (second occurrence)
        assert '"description": "Created"' in prompt
        assert '"tags": ["users"]' in prompt
        assert '"tags": ["dashboard"]' in prompt

        # Check that the prompt contains the schemas
        assert '"#/components/schemas/Data"' in prompt
        assert '"#/components/schemas/Activity"' in prompt

        # Check that the prompt contains the parameters
        assert '"$ref": "#/components/parameters/UsernamePath"' in prompt
        assert '"$ref": "#/components/parameters/ActivityTypePath"' in prompt
        assert '"$ref": "#/components/parameters/Limit"' in prompt
        assert '"$ref": "#/components/parameters/DashboardIDPath"' in prompt

        # Check that the prompt contains all status responses and their descriptions
        assert '"200": {' in prompt
        assert '"description": "An array of activities"' in prompt
        assert '"401": {' in prompt
        assert '"description": "Unauthorized"' in prompt
        assert '"403": {' in prompt
        assert '"description": "Forbidden"' in prompt
        assert '"404": {' in prompt
        assert '"description": "Not Found"' in prompt
        assert '"500": {' in prompt
        assert '"description": "Server Error"' in prompt

        # Check that the prompt contains the request body for 'activity'
        assert '"activity": {' in prompt
        assert '"required": true' in prompt or '"required": True' in prompt
        assert '"application/json": {' in prompt
        assert '"$ref": "#/components/schemas/Activity"' in prompt

        # Check that the prompt contains the metadata
        assert "Test API" in prompt
        assert "1.0.0" in prompt
        assert "This is a test API" in prompt
        assert "https://example.com/terms" in prompt
        assert "John Doe" in prompt
        assert "https://johndoe.com" in prompt
        assert "MIT" in prompt
        assert "https://mit.com" in prompt
        assert "https://api.example.com" in prompt
        assert "apiKey" in prompt
        assert "discoveryresources" in prompt
        assert "metadataresources" in prompt
        assert "http://example.com/docs/read/ProgrammesAPIGuide" in prompt

        # Check that the prompt contains the workflows(optional)
        assert "desc1" in prompt
        assert "desc2" in prompt
