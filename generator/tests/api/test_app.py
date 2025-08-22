import inspect
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from arazzo_generator.api.app import GenerateRequest, app
from arazzo_generator.generator.generator_service import generate_arazzo


# Testing the API root endpoint
def test_root():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Arazzo Generator API"
    assert data["version"] == "1.0.0"
    assert "description" in data


# Testing the /generate endpoint with a successful response
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_success(mock_generate):
    # Mock return values: (arazzo_spec, arazzo_content, is_valid, validation_errors, fallback_used)
    mock_generate.return_value = ({"mock": "spec"}, "mock content", True, [], False)
    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": None,
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_valid"] is True
    assert data["arazzo_spec"] == {"mock": "spec"}
    assert data["content"] == "mock content"


# Test /generate returns 500 with 'Failed to generate valid Arazzo specification' when arazzo_spec is None
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_arazzo_spec_none(mock_generate):
    mock_generate.return_value = (None, None, False, ["some error"], True)
    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": None,
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert (
        data["detail"]
        == "Error generating Arazzo specification: 500: Failed to generate valid Arazzo specification"
    )


# Test /generate returns 500 with 'Error generating Arazzo specification: ...' when an exception is raised
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_arazzo_exception(mock_generate):
    mock_generate.side_effect = RuntimeError("unexpected failure")
    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": None,
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Error generating Arazzo specification: unexpected failure"


# Test /generate returns 422 with 'Invalid URL' when the URL is invalid
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_invalid_url(mock_generate):
    payload = {
        "url": "ftp://invalid-url.com/openapi.json",  # Invalid scheme
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": None,
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    # data["detail"] is a list of error dicts from Pydantic
    assert any("Value error" in err["msg"] for err in data["detail"])
    assert any("URL scheme" in err["msg"] for err in data["detail"])


# Test that API and service parameters match
def test_api_and_service_parameters_match():
    # Get GenerateRequest fields (as used by the API)
    request_fields = set(GenerateRequest.model_fields.keys())

    # Get generate_arazzo parameter names (as used by the service)
    service_params = set(inspect.signature(generate_arazzo).parameters.keys())

    # If 'verbose' is not exposed via API, remove it from service_params
    service_params.discard("verbose")
    # _fallback_attempt is an internal flag not exposed via the public API
    service_params.discard("_fallback_attempt")
    # output is used by CLI but not by API (API returns content directly)
    service_params.discard("output")

    # If there are any fields in request_fields not used by the service, remove them
    # (e.g., if the API has extra fields for request validation only)
    # request_fields.discard('some_extra_field')

    assert request_fields == service_params, (
        f"API fields: {request_fields}\n"
        f"Service params: {service_params}\n"
        "Mismatch between API request model and service function parameters"
    )


# Workflow descriptions are optional so empty arrays should not cause a status error
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_workflow_descriptions_empty(mock_generate):
    mock_generate.return_value = ({"mock": "spec"}, "mock content", True, [], False)
    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": [],  # Valid empty list
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["fallback_used"] is False
    assert data["validation_errors"] == []


# Workflow descriptions are valid strings so should not cause a status error
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_workflow_descriptions_success(mock_generate):
    mock_generate.return_value = ({"mock": "spec"}, "mock content", True, [], False)
    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": [
            "description1",
            "description2",
        ],  # Valid string workflow descriptions
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_errors"] == []


# Workflow descriptions invalid type (not strings) so should cause a status error
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_workflow_descriptions_with_non_string_elements(mock_generate):
    mock_generate.return_value = (
        {"mock": "spec"},
        "mock content",
        True,
        ["some error"],
        True,
    )

    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": [123, None],  # Invalid contents
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("workflow_descriptions" in str(err["loc"]) for err in data["detail"])


# Workflow descriptions contains empty strings, will still work because LLM workflow generation still occurs
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_workflow_descriptions_with_empty_strings(mock_generate):
    mock_generate.return_value = ({"mock": "spec"}, "mock content", True, [], True)

    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": [
            "",
            "",
        ],  # Contains empty strings, LLM generation will still generate
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["validation_errors"] == []
    assert data["fallback_used"] is True
    assert "Initial generation using provided workflow descriptions failed" in data.get(
        "message", ""
    )


# Test service fallback handling via API when invalid custom workflow descriptions used
@patch("arazzo_generator.api.app.generate_arazzo")
def test_generate_fallback_used_invalid_workflow_descriptions(mock_generate):
    """Should return fallback_used True and an explanatory message when service triggers fallback."""
    mock_generate.return_value = (
        {"mock": "spec"},
        "mock content",
        True,
        [],
        True,  # fallback_used
    )

    payload = {
        "url": "http://example.com/openapi.json",
        "format": "json",
        "validate_spec": True,
        "direct_llm": False,
        "api_key": None,
        "llm_model": None,
        "llm_provider": "anthropic",
        "workflow_descriptions": ["invalid workflow description"],
    }
    with TestClient(app) as client:
        response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["fallback_used"] is True
    assert "Initial generation using provided workflow descriptions failed" in data.get(
        "message", ""
    )
