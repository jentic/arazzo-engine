"""Tests for the ArazzoSerializer class."""

import json
import unittest

import yaml

from arazzo_generator.utils.serializer import ArazzoSerializer


class TestArazzoSerializer(unittest.TestCase):
    """Tests for the ArazzoSerializer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample Arazzo specification
        self.arazzo_spec = {
            "arazzo": "1.0",
            "info": {
                "title": "Pet Store API",
                "description": "A sample API for managing pets",
                "version": "1.0.0",
            },
            "workflows": [
                {
                    "id": "pet-management",
                    "description": "Manage pets in the pet store",
                    "steps": [
                        {
                            "stepId": "list-pets",
                            "description": "List all pets",
                            "operation": {
                                "operationId": "listPets",
                                "path": "/pets",
                                "method": "get",
                            },
                            "outputs": {
                                "pets_list": "$response.body",
                                "count": "$response.body.length",
                            },
                        },
                        {
                            "stepId": "get-pet",
                            "description": "Get a specific pet",
                            "operation": {
                                "operationId": "getPetById",
                                "path": "/pets/{petId}",
                                "method": "get",
                            },
                            "parameters": [
                                {
                                    "name": "petId",
                                    "value": "$steps.list-pets.outputs.pets_list[0].id",
                                }
                            ],
                            "outputs": {"pet_details": "$response.body"},
                        },
                    ],
                }
            ],
        }

        # Arazzo specification with long output references
        self.arazzo_spec_with_long_refs = {
            "arazzo": "1.0",
            "workflows": [
                {
                    "id": "workflow-with-long-refs",
                    "steps": [
                        {
                            "stepId": "step1",
                            "outputs": {
                                "output1": "$response.body",
                                "output2": "$response.body.items",
                                "output3": "$response.body.items[0].deeply.nested.property",
                            },
                        },
                        {
                            "stepId": "step2",
                            "parameters": [
                                {
                                    "name": "param1",
                                    "value": "$steps.step1.outputs.output3.very.deeply.nested.property.that.could.wrap",
                                }
                            ],
                        },
                    ],
                }
            ],
        }

    def test_to_yaml_with_valid_spec(self):
        """Test the to_yaml method with a valid Arazzo specification."""
        # Convert the Arazzo specification to YAML
        yaml_str = ArazzoSerializer.to_yaml(self.arazzo_spec)

        # Verify that the YAML string is not empty
        self.assertTrue(yaml_str)

        # Parse the YAML string back to a dictionary
        parsed_spec = yaml.safe_load(yaml_str)

        # Verify that the parsed specification matches the original
        self.assertEqual(parsed_spec, self.arazzo_spec)

        # Verify that the YAML string contains the expected content
        self.assertIn("arazzo: '1.0'", yaml_str)
        self.assertIn("id: pet-management", yaml_str)
        self.assertIn("stepId: list-pets", yaml_str)
        self.assertIn("$steps.list-pets.outputs.pets_list[0].id", yaml_str)

    def test_to_yaml_with_empty_spec(self):
        """Test the to_yaml method with an empty Arazzo specification."""
        # Convert an empty specification to YAML
        yaml_str = ArazzoSerializer.to_yaml({})

        # Verify that the YAML string is empty
        self.assertEqual(yaml_str, "")

        # Convert a None specification to YAML
        yaml_str = ArazzoSerializer.to_yaml(None)

        # Verify that the YAML string is empty
        self.assertEqual(yaml_str, "")

    def test_to_yaml_with_long_references(self):
        """Test the to_yaml method with long output references."""
        # Convert the Arazzo specification with long references to YAML
        yaml_str = ArazzoSerializer.to_yaml(self.arazzo_spec_with_long_refs)

        # Verify that the YAML string is not empty
        self.assertTrue(yaml_str)

        # Verify that the long reference is on a single line
        self.assertIn(
            '"$steps.step1.outputs.output3.very.deeply.nested.property.that.could.wrap"',
            yaml_str,
        )

        # Parse the YAML string back to a dictionary
        parsed_spec = yaml.safe_load(yaml_str)

        # Verify that the parsed specification matches the original
        self.assertEqual(parsed_spec, self.arazzo_spec_with_long_refs)

    def test_to_json_with_valid_spec(self):
        """Test the to_json method with a valid Arazzo specification."""
        # Convert the Arazzo specification to JSON
        json_str = ArazzoSerializer.to_json(self.arazzo_spec)

        # Verify that the JSON string is not empty
        self.assertTrue(json_str)

        # Parse the JSON string back to a dictionary
        parsed_spec = json.loads(json_str)

        # Verify that the parsed specification matches the original
        self.assertEqual(parsed_spec, self.arazzo_spec)

        # Verify that the JSON string contains the expected content
        self.assertIn('"arazzo": "1.0"', json_str)
        self.assertIn('"id": "pet-management"', json_str)
        self.assertIn('"stepId": "list-pets"', json_str)
        self.assertIn('"$steps.list-pets.outputs.pets_list[0].id"', json_str)

    def test_to_json_with_empty_spec(self):
        """Test the to_json method with an empty Arazzo specification."""
        # Convert an empty specification to JSON
        json_str = ArazzoSerializer.to_json({})

        # Verify that the JSON string is an empty object
        self.assertEqual(json_str, "{}")

        # Convert a None specification to JSON
        json_str = ArazzoSerializer.to_json(None)

        # Verify that the JSON string is an empty object
        self.assertEqual(json_str, "{}")

    def test_to_json_with_long_references(self):
        """Test the to_json method with long output references."""
        # Convert the Arazzo specification with long references to JSON
        json_str = ArazzoSerializer.to_json(self.arazzo_spec_with_long_refs)

        # Verify that the JSON string is not empty
        self.assertTrue(json_str)

        # Verify that the long reference is preserved
        self.assertIn(
            '"$steps.step1.outputs.output3.very.deeply.nested.property.that.could.wrap"',
            json_str,
        )

        # Parse the JSON string back to a dictionary
        parsed_spec = json.loads(json_str)

        # Verify that the parsed specification matches the original
        self.assertEqual(parsed_spec, self.arazzo_spec_with_long_refs)


if __name__ == "__main__":
    unittest.main()
