"""Tests for the utility functions in the generator module."""

import unittest

import yaml

from arazzo_generator.utils.utils import encode_json_pointer, to_kebab_case
from arazzo_generator.utils.yaml_utils import NoWrapSafeDumper, fix_output_references


class TestUtils(unittest.TestCase):
    """Tests for the utility functions in the generator module."""

    def test_to_kebab_case(self):
        """Test the to_kebab_case function."""
        # Test camelCase
        self.assertEqual(to_kebab_case("camelCase"), "camel-case")

        # Test PascalCase
        self.assertEqual(to_kebab_case("PascalCase"), "pascal-case")

        # Test snake_case
        self.assertEqual(to_kebab_case("snake_case"), "snake-case")

        # Test space-separated
        self.assertEqual(to_kebab_case("space separated"), "space-separated")

        # Test mixed case with numbers
        self.assertEqual(
            to_kebab_case("mixedCase123With_underscores"),
            "mixed-case123-with-underscores",
        )

        # Test with special characters
        self.assertEqual(to_kebab_case("special@#characters!"), "specialcharacters")

        # Test with leading and trailing hyphens
        self.assertEqual(to_kebab_case("-leading-trailing-"), "leading-trailing")

        # Test empty string
        self.assertEqual(to_kebab_case(""), "")

        # Test workflow names
        self.assertEqual(to_kebab_case("Pet Management"), "pet-management")
        self.assertEqual(to_kebab_case("UserAuthentication"), "user-authentication")
        self.assertEqual(to_kebab_case("CRUD_Operations"), "crud-operations")

    def test_encode_json_pointer(self):
        """Test the encode_json_pointer function."""
        # Test with no special characters
        self.assertEqual(encode_json_pointer("normal"), "normal")

        # Test with tilde (~)
        self.assertEqual(encode_json_pointer("with~tilde"), "with~0tilde")

        # Test with forward slash (/)
        self.assertEqual(encode_json_pointer("with/slash"), "with~1slash")

        # Test with both tilde and forward slash
        self.assertEqual(encode_json_pointer("with~/both"), "with~0~1both")

        # Test empty string
        self.assertEqual(encode_json_pointer(""), "")

        # Test JSON path segments
        self.assertEqual(encode_json_pointer("properties/items"), "properties~1items")
        self.assertEqual(encode_json_pointer("schema~reference"), "schema~0reference")

    def test_fix_output_references(self):
        """Test the fix_output_references function."""
        # Test with a broken reference (split across lines)
        broken_yaml = """
steps:
  - stepId: step1
    outputs:
      output1: $response.body
  - stepId: step2
    parameters:
      - name: param1
        value: $steps.step1.outputs.
          output1
"""
        fixed_yaml = fix_output_references(broken_yaml)
        self.assertIn("$steps.step1.outputs. output1", fixed_yaml)

        # Test with a reference that's already correct
        correct_yaml = """
steps:
  - stepId: step1
    outputs:
      output1: $response.body
  - stepId: step2
    parameters:
      - name: param1
        value: $steps.step1.outputs.output1
"""
        fixed_yaml = fix_output_references(correct_yaml)
        self.assertIn("$steps.step1.outputs.output1", fixed_yaml)

        # Test with multiple broken references
        multiple_broken_yaml = """
steps:
  - stepId: step1
    outputs:
      output1: $response.body
      output2: $response.headers
  - stepId: step2
    parameters:
      - name: param1
        value: $steps.step1.outputs.
          output1
      - name: param2
        value: $steps.step1.outputs.
          output2
"""
        fixed_yaml = fix_output_references(multiple_broken_yaml)
        self.assertIn("$steps.step1.outputs. output1", fixed_yaml)
        self.assertIn("$steps.step1.outputs. output2", fixed_yaml)

    def test_no_wrap_safe_dumper(self):
        """Test the NoWrapSafeDumper class."""
        # Create a dictionary with a reference
        data = {
            "steps": [
                {"stepId": "step1", "outputs": {"output1": "$response.body"}},
                {
                    "stepId": "step2",
                    "parameters": [{"name": "param1", "value": "$steps.step1.outputs.output1"}],
                },
            ]
        }

        # Dump the dictionary using the NoWrapSafeDumper
        yaml_str = yaml.dump(data, Dumper=NoWrapSafeDumper)

        # Verify that the reference is on a single line
        self.assertIn('"$steps.step1.outputs.output1"', yaml_str)

        # Verify that the dumper works with nested references
        data["steps"][1]["parameters"][0]["value"] = "$steps.step1.outputs.output1.nested.property"
        yaml_str = yaml.dump(data, Dumper=NoWrapSafeDumper)
        self.assertIn('"$steps.step1.outputs.output1.nested.property"', yaml_str)

        # Verify that non-reference strings are not quoted
        data["steps"][1]["parameters"][0]["value"] = "simple string"
        yaml_str = yaml.dump(data, Dumper=NoWrapSafeDumper)
        self.assertIn("simple string", yaml_str)
        self.assertNotIn('"simple string"', yaml_str)


if __name__ == "__main__":
    unittest.main()
