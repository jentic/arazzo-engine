"""Tests for the exceptions module."""

import unittest

import pytest

from arazzo_generator.utils.exceptions import (
    ArazzoError,
    InvalidUserWorkflowError,
    SpecValidationError,
)


class TestArazzoExceptions(unittest.TestCase):
    def test_arazzo_error(self):
        """Test base ArazzoError exception."""
        with pytest.raises(ArazzoError):
            raise ArazzoError("Test error")

    def test_invalid_user_workflow_default(self):
        """Test InvalidUserWorkflowError with default parameters."""
        with pytest.raises(InvalidUserWorkflowError) as exc_info:
            raise InvalidUserWorkflowError()

        assert exc_info.value.requested_workflows == []
        assert "No valid workflows identified" in str(exc_info.value)

    def test_invalid_user_workflow_with_workflows(self):
        """Test InvalidUserWorkflowError with specific workflows."""
        workflows = ["workflow1", "workflow2"]
        with pytest.raises(InvalidUserWorkflowError) as exc_info:
            raise InvalidUserWorkflowError(workflows)

        assert exc_info.value.requested_workflows == workflows

    def test_spec_validation_error(self):
        """Test SpecValidationError with validation errors."""
        errors = ["Error 1", "Error 2"]
        with pytest.raises(SpecValidationError) as exc_info:
            raise SpecValidationError(errors)

        assert exc_info.value.validation_errors == errors
        assert "Arazzo specification failed validation" in str(exc_info.value)

    def test_exception_hierarchy(self):
        """Test that custom exceptions inherit from ArazzoError."""
        assert issubclass(InvalidUserWorkflowError, ArazzoError)
        assert issubclass(SpecValidationError, ArazzoError)

        # Verify they can be caught as ArazzoError
        with pytest.raises(ArazzoError):
            raise InvalidUserWorkflowError()

        with pytest.raises(ArazzoError):
            raise SpecValidationError(["Test error"])
