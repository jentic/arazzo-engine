import pytest

from arazzo_runner.evaluator import ExpressionEvaluator
from arazzo_runner.models import ExecutionState


@pytest.fixture
def state():
    # Simulate the in-memory state as it exists after a step runs
    s = ExecutionState(workflow_id="demo")
    s.step_outputs = {"findPetsStep": {"statusCode": 200, "responseBody": [{"id": 1}, {"id": 2}]}}
    return s


@pytest.fixture
def template_state():
    """State fixture for template expression tests."""
    s = ExecutionState(workflow_id="test")
    s.inputs = {
        "userId": "user-123",
        "date": "2024-01-15",
        "prefix": "doc",
    }
    s.step_outputs = {
        "api-step": {
            "resourceId": "res-456",
            "version": "v2",
        }
    }
    return s


@pytest.mark.parametrize(
    "expr,expected",
    [
        # Root-dot normalization: should handle leading '$.'
        ("$.steps.findPetsStep.statusCode", 200),
        # Redundant 'outputs' segment: should skip 'outputs' if not present in dict
        ("$.steps.findPetsStep.outputs.statusCode", 200),
        ("$steps.findPetsStep.outputs.statusCode", 200),
        # Both fixes together: verbose form with array output
        ("$.steps.findPetsStep.outputs.responseBody", [{"id": 1}, {"id": 2}]),
    ],
)
def test_evaluator_path_variants(state, expr, expected):
    result = ExpressionEvaluator.evaluate_expression(expr, state)
    assert result == expected, f"Expression '{expr}' should resolve to {expected}, got {result}"


class TestTemplateExpressionsInDictArray:
    """Tests for template expression handling in dict and array values."""

    def test_template_in_dict_value_single(self, template_state):
        """Test single template expression in a dict value."""
        obj = {"name": "file-{$inputs.userId}.txt"}

        result = ExpressionEvaluator.process_object_expressions(obj, template_state)

        assert result["name"] == "file-user-123.txt"

    def test_template_in_dict_value_multiple(self, template_state):
        """Test multiple template expressions in a single dict value."""
        obj = {"path": "{$inputs.prefix}-{$inputs.userId}-{$inputs.date}"}

        result = ExpressionEvaluator.process_object_expressions(obj, template_state)

        assert result["path"] == "doc-user-123-2024-01-15"

    def test_template_in_dict_value_with_step_output(self, template_state):
        """Test template expression referencing step outputs."""
        obj = {
            "url": "/api/{$steps.api-step.outputs.version}/resources/{$steps.api-step.outputs.resourceId}"
        }

        result = ExpressionEvaluator.process_object_expressions(obj, template_state)

        assert result["url"] == "/api/v2/resources/res-456"

    def test_template_in_nested_dict(self, template_state):
        """Test template expression in nested dict."""
        obj = {"metadata": {"filename": "report-{$inputs.date}.pdf"}}

        result = ExpressionEvaluator.process_object_expressions(obj, template_state)

        assert result["metadata"]["filename"] == "report-2024-01-15.pdf"

    def test_template_in_array_item(self, template_state):
        """Test template expression in array item."""
        arr = ["prefix-{$inputs.userId}", "static-value", "{$inputs.date}-suffix"]

        result = ExpressionEvaluator.process_array_expressions(arr, template_state)

        assert result[0] == "prefix-user-123"
        assert result[1] == "static-value"
        assert result[2] == "2024-01-15-suffix"

    def test_template_in_dict_within_array(self, template_state):
        """Test template expression in dict within array."""
        arr = [
            {"name": "item-{$inputs.userId}"},
            {"id": "{$steps.api-step.outputs.resourceId}"},
        ]

        result = ExpressionEvaluator.process_array_expressions(arr, template_state)

        assert result[0]["name"] == "item-user-123"
        assert result[1]["id"] == "res-456"

    def test_direct_expression_still_works(self, template_state):
        """Test that direct expressions (starting with $) still work."""
        obj = {
            "userId": "$inputs.userId",
            "resourceId": "$steps.api-step.outputs.resourceId",
        }

        result = ExpressionEvaluator.process_object_expressions(obj, template_state)

        assert result["userId"] == "user-123"
        assert result["resourceId"] == "res-456"

    def test_mixed_direct_and_template_expressions(self, template_state):
        """Test mix of direct and template expressions."""
        obj = {
            "directValue": "$inputs.userId",
            "templateValue": "user-{$inputs.userId}-data",
            "staticValue": "no-expression-here",
        }

        result = ExpressionEvaluator.process_object_expressions(obj, template_state)

        assert result["directValue"] == "user-123"
        assert result["templateValue"] == "user-user-123-data"
        assert result["staticValue"] == "no-expression-here"

    def test_template_with_none_value(self, template_state):
        """Test template expression that evaluates to None."""
        obj = {"value": "prefix-{$inputs.nonexistent}-suffix"}

        result = ExpressionEvaluator.process_object_expressions(obj, template_state)

        # None should be replaced with empty string
        assert result["value"] == "prefix--suffix"
