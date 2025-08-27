"""Tests for the Arazzo validator module."""

import unittest
from unittest.mock import MagicMock

import yaml

from arazzo_generator.validator.arazzo_validator import ArazzoValidator


class TestArazzoValidator(unittest.TestCase):
    """Tests for the ArazzoValidator class."""

    def setUp(self):
        """Set up the test case."""
        # Reset any class variables or state before each test
        pass

    def test_load_schema(self):
        """Test loading the Arazzo schema."""
        # Prepare test data
        test_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"arazzo": {"type": "string"}},
            "required": ["arazzo"],
        }

        # Create validator with a patched load_schema method
        validator = ArazzoValidator()
        validator.load_schema = MagicMock(return_value=test_schema)

        # Call load_schema
        schema = validator.load_schema()

        # Check schema
        self.assertIsNotNone(schema)
        self.assertEqual(schema["type"], "object")
        self.assertIn("arazzo", schema["properties"])

    def test_validate_valid_spec(self):
        """Test validating a valid Arazzo spec."""
        # Prepare test schema
        test_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "arazzo": {"type": "string"},
                "info": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"},
                    },
                    "required": ["title", "version"],
                },
                "sourceDescriptions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "url": {"type": "string"},
                        },
                        "required": ["name", "url"],
                    },
                },
                "workflows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "workflowId": {"type": "string"},
                            "steps": {"type": "array"},
                        },
                        "required": ["workflowId", "steps"],
                    },
                },
            },
            "required": ["arazzo", "info", "sourceDescriptions", "workflows"],
        }

        # Create valid spec
        valid_spec = {
            "arazzo": "1.0.0",
            "info": {"title": "Test Arazzo Spec", "version": "1.0.0"},
            "sourceDescriptions": [
                {"name": "test_source", "url": "https://example.com/openapi.json"}
            ],
            "workflows": [
                {
                    "workflowId": "test_workflow",
                    "steps": [{"stepId": "test_step", "operationId": "testOperation"}],
                }
            ],
        }

        # Create validator with the test schema
        validator = ArazzoValidator()
        validator.schema = test_schema  # Set schema directly

        # Validate spec
        is_valid = validator.validate(valid_spec)

        # Check result
        self.assertTrue(is_valid)

    def test_validate_invalid_spec(self):
        """Test validating an invalid Arazzo spec."""
        # Prepare test schema
        test_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "arazzo": {"type": "string"},
                "info": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"},
                    },
                    "required": ["title", "version"],
                },
                "sourceDescriptions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "url": {"type": "string"},
                        },
                        "required": ["name", "url"],
                    },
                },
                "workflows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "workflowId": {"type": "string"},
                            "steps": {"type": "array"},
                        },
                        "required": ["workflowId", "steps"],
                    },
                },
            },
            "required": ["arazzo", "info", "sourceDescriptions", "workflows"],
        }

        # Create invalid spec
        invalid_spec = {
            "arazzo": "1.0.0",
            # Missing info
            "sourceDescriptions": [
                {"name": "test_source", "url": "https://example.com/openapi.json"}
            ],
            "workflows": [
                {
                    "workflowId": "test_workflow",
                    "steps": [{"stepId": "test_step", "operationId": "testOperation"}],
                }
            ],
        }

        # Create validator with the test schema
        validator = ArazzoValidator()
        validator.schema = test_schema  # Set schema directly

        # Validate spec
        is_valid = validator.validate(invalid_spec)

        # Check result
        self.assertFalse(is_valid)

    def test_get_validation_errors(self):
        """Test getting validation errors for an invalid Arazzo spec."""
        # Prepare test schema
        test_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "arazzo": {"type": "string"},
                "info": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"},
                    },
                    "required": ["title", "version"],
                },
                "sourceDescriptions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "url": {"type": "string"},
                        },
                        "required": ["name", "url"],
                    },
                },
                "workflows": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "workflowId": {"type": "string"},
                            "steps": {"type": "array", "minItems": 1},
                        },
                        "required": ["workflowId", "steps"],
                    },
                },
            },
            "required": ["arazzo", "info", "sourceDescriptions", "workflows"],
        }

        # Create invalid spec with multiple errors
        invalid_spec = {
            "arazzo": "1.0.0",
            "info": {
                "title": "Test Arazzo Spec"
                # Missing version
            },
            "sourceDescriptions": [
                {
                    "url": "https://example.com/openapi.json"
                    # Missing name
                }
            ],
            "workflows": [{"workflowId": "test_workflow", "steps": []}],  # Empty steps array
        }

        # Create validator with the test schema
        validator = ArazzoValidator()
        validator.schema = test_schema  # Set schema directly

        # Get validation errors
        errors = validator.get_validation_errors(invalid_spec)

        # Print errors for debugging
        print("\nValidation errors:")
        for error in errors:
            print(f"  - {error}")

        # Check errors
        self.assertGreaterEqual(len(errors), 3)  # At least 3 errors

        # Check for specific error messages based on the actual format returned by the validator
        # The format is "path: message" where path is the JSON path to the error
        info_error = any("info" in error and "version" in error for error in errors)
        source_error = any("sourceDescriptions/0" in error and "name" in error for error in errors)
        steps_error = any("workflows/0/steps" in error and "non-empty" in error for error in errors)

        self.assertTrue(info_error, "No error found for missing version in info")
        self.assertTrue(source_error, "No error found for missing name in sourceDescriptions")
        self.assertTrue(steps_error, "No error found for empty steps array")

    def test_validate_yaml_string(self):
        """Test validating an Arazzo spec as a YAML string."""
        # Create validator with mock schema
        validator = ArazzoValidator()
        validator.schema = {
            "type": "object",
            "properties": {
                "arazzo": {"type": "string"},
                "info": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"},
                    },
                    "required": ["title", "version"],
                },
            },
            "required": ["arazzo", "info"],
        }

        # Create valid spec as YAML string
        valid_yaml = yaml.dump(
            {
                "arazzo": "1.0.0",
                "info": {"title": "Test Arazzo Spec", "version": "1.0.0"},
            }
        )

        # Validate spec
        is_valid = validator.validate(valid_yaml)

        # Check result
        self.assertTrue(is_valid)
