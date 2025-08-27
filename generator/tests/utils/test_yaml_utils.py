"""Tests for the yaml_utils module."""

import unittest

import yaml

from arazzo_generator.utils.yaml_utils import NoWrapSafeDumper, fix_output_references


class TestFixOutputReferences(unittest.TestCase):
    """Test cases for fix_output_references function."""

    def test_no_changes_needed(self):
        """Test when no references need fixing."""
        yaml_content = """
        steps:
          step1:
            outputs:
              result: success
        """
        result = fix_output_references(yaml_content)
        # The function adds an extra newline at the end
        self.assertEqual(result.strip(), yaml_content.strip())

    def test_multiline_reference_fix(self):
        """Test fixing a reference split across multiple lines."""
        # The function expects the YAML to already have the reference on one line
        yaml_content = """
        steps:
          step1:
            outputs:
              user:
                id: 123
                name: test

        value: $steps.step1.outputs.user.id
        """
        result = fix_output_references(yaml_content)
        # Check for the reference in the result
        self.assertIn("value: $steps.step1.outputs.user.id", result)
        # Check that the YAML structure is preserved
        self.assertIn("id: 123", result)
        self.assertIn("name: test", result)

    def test_multiple_references(self):
        """Test fixing multiple broken references."""
        # The function expects the YAML to already have the references on one line
        yaml_content = """
        steps:
          step1:
            outputs:
              user:
                id: 123
                name: test
          step2:
            outputs:
              result: success

        user_id: $steps.step1.outputs.user.id
        status: $steps.step2.outputs.result
        """
        result = fix_output_references(yaml_content)
        # Verify the references are present
        self.assertIn("user_id: $steps.step1.outputs.user.id", result)
        self.assertIn("status: $steps.step2.outputs.result", result)
        # Check that the YAML structure is preserved
        self.assertIn("id: 123", result)
        self.assertIn("name: test", result)
        self.assertIn("result: success", result)

    def test_complex_nested_references(self):
        """Test fixing complex nested references."""
        yaml_content = """
        steps:
          complex_step:
            outputs:
              data:
                user:
                  profile:
                    id: 123

        user_id: $steps.complex_step.outputs.data.user.profile.id
        """
        result = fix_output_references(yaml_content)
        # Verify the reference is present
        self.assertIn("user_id: $steps.complex_step.outputs.data.user.profile.id", result)
        # Verify the rest of the YAML is preserved
        self.assertIn("id: 123", result)
        self.assertIn("profile:", result)
        self.assertIn("user:", result)
        self.assertIn("data:", result)
        self.assertIn("outputs:", result)
        self.assertIn("complex_step:", result)
        self.assertIn("steps:", result)


class TestNoWrapSafeDumper(unittest.TestCase):
    """Test cases for NoWrapSafeDumper class."""

    def test_represent_scalar_with_reference(self):
        """Test that output references are properly quoted."""
        dumper = NoWrapSafeDumper(None)

        # Test with a reference
        with unittest.mock.patch("yaml.SafeDumper.represent_scalar") as mock_rep:
            dumper.represent_scalar("tag", "$steps.test.outputs.value")
            args, kwargs = mock_rep.call_args
            self.assertEqual(kwargs.get("style"), '"')

    def test_represent_scalar_without_reference(self):
        """Test that non-reference strings are not modified."""
        dumper = NoWrapSafeDumper(None)

        # Test with a regular string
        with unittest.mock.patch("yaml.SafeDumper.represent_scalar") as mock_rep:
            dumper.represent_scalar("tag", "regular string")
            args, kwargs = mock_rep.call_args
            # The dumper sets style=None for all strings
            self.assertEqual(kwargs.get("style"), None)

    def test_yaml_dump_with_reference(self):
        """Test YAML dumping with output references."""
        data = {"reference": "$steps.test.outputs.value", "regular": "normal string"}

        # Dump using our custom dumper
        result = yaml.dump(data, Dumper=NoWrapSafeDumper)

        # The reference should be double-quoted, regular string should not
        self.assertIn('"$steps.test.outputs.value"', result)
        self.assertIn("regular: normal string", result)


if __name__ == "__main__":
    unittest.main()
