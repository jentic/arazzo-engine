"""Tests for the ArazzoComponentsBuilder class."""

import unittest

from arazzo_generator.generator.components import ArazzoComponentsBuilder


class TestArazzoComponentsBuilder(unittest.TestCase):
    """Tests for the ArazzoComponentsBuilder class."""

    def test_create_action_end(self):
        """Test creating an 'end' action."""
        # Create a simple 'end' action
        action = ArazzoComponentsBuilder.create_action(
            action_type="end", name="test_end_action", action_definition={}
        )

        # Verify the action properties
        self.assertEqual(action["type"], "end")
        self.assertEqual(action["name"], "test_end_action")
        self.assertEqual(len(action), 2)  # Only type and name

        # Create an 'end' action with criteria
        action = ArazzoComponentsBuilder.create_action(
            action_type="end",
            name="test_end_action_with_criteria",
            action_definition={"criteria": [{"condition": "$statusCode == 404"}]},
        )

        # Verify the action properties
        self.assertEqual(action["type"], "end")
        self.assertEqual(action["name"], "test_end_action_with_criteria")
        self.assertEqual(len(action["criteria"]), 1)
        self.assertEqual(action["criteria"][0]["condition"], "$statusCode == 404")

    def test_create_action_retry(self):
        """Test creating a 'retry' action."""
        # Create a 'retry' action
        action = ArazzoComponentsBuilder.create_action(
            action_type="retry",
            name="test_retry_action",
            action_definition={"retryAfter": 2, "retryLimit": 3},
        )

        # Verify the action properties
        self.assertEqual(action["type"], "retry")
        self.assertEqual(action["name"], "test_retry_action")
        self.assertEqual(action["retryAfter"], 2)
        self.assertEqual(action["retryLimit"], 3)

        # Create a 'retry' action with criteria
        action = ArazzoComponentsBuilder.create_action(
            action_type="retry",
            name="test_retry_action_with_criteria",
            action_definition={
                "retryAfter": 5,
                "retryLimit": 2,
                "criteria": [{"condition": "$statusCode >= 500"}],
            },
        )

        # Verify the action properties
        self.assertEqual(action["type"], "retry")
        self.assertEqual(action["name"], "test_retry_action_with_criteria")
        self.assertEqual(action["retryAfter"], 5)
        self.assertEqual(action["retryLimit"], 2)
        self.assertEqual(len(action["criteria"]), 1)
        self.assertEqual(action["criteria"][0]["condition"], "$statusCode >= 500")

    def test_create_action_goto(self):
        """Test creating a 'goto' action."""
        # Create a 'goto' action
        action = ArazzoComponentsBuilder.create_action(
            action_type="goto",
            name="test_goto_action",
            action_definition={"stepId": "target_step"},
        )

        # Verify the action properties
        self.assertEqual(action["type"], "goto")
        self.assertEqual(action["name"], "test_goto_action")
        self.assertEqual(action["stepId"], "target_step")

        # Create a 'goto' action with criteria
        action = ArazzoComponentsBuilder.create_action(
            action_type="goto",
            name="test_goto_action_with_criteria",
            action_definition={
                "stepId": "error_handler_step",
                "criteria": [{"condition": "$statusCode == 429"}],
            },
        )

        # Verify the action properties
        self.assertEqual(action["type"], "goto")
        self.assertEqual(action["name"], "test_goto_action_with_criteria")
        self.assertEqual(action["stepId"], "error_handler_step")
        self.assertEqual(len(action["criteria"]), 1)
        self.assertEqual(action["criteria"][0]["condition"], "$statusCode == 429")

    def test_build_default_components(self):
        """Test building the default components section."""
        # Build the default components
        components = ArazzoComponentsBuilder.build_default_components()

        # Verify the top-level structure
        self.assertIn("components", components)
        self.assertIn("successActions", components["components"])
        self.assertIn("failureActions", components["components"])

        # Verify success actions
        success_actions = components["components"]["successActions"]
        self.assertIn("default_success", success_actions)
        self.assertEqual(success_actions["default_success"]["type"], "end")
        self.assertEqual(success_actions["default_success"]["name"], "default_success")

        # Verify failure actions
        failure_actions = components["components"]["failureActions"]

        # Check auth_failure action
        self.assertIn("auth_failure", failure_actions)
        self.assertEqual(failure_actions["auth_failure"]["type"], "end")
        self.assertEqual(failure_actions["auth_failure"]["name"], "auth_failure")
        self.assertEqual(
            failure_actions["auth_failure"]["criteria"][0]["condition"],
            "$statusCode == 401",
        )

        # Check permission_denied action
        self.assertIn("permission_denied", failure_actions)
        self.assertEqual(failure_actions["permission_denied"]["type"], "end")
        self.assertEqual(failure_actions["permission_denied"]["name"], "permission_denied")
        self.assertEqual(
            failure_actions["permission_denied"]["criteria"][0]["condition"],
            "$statusCode == 403",
        )

        # Check not_found action
        self.assertIn("not_found", failure_actions)
        self.assertEqual(failure_actions["not_found"]["type"], "end")
        self.assertEqual(failure_actions["not_found"]["name"], "not_found")
        self.assertEqual(
            failure_actions["not_found"]["criteria"][0]["condition"],
            "$statusCode == 404",
        )

        # Check server_error action
        self.assertIn("server_error", failure_actions)
        self.assertEqual(failure_actions["server_error"]["type"], "retry")
        self.assertEqual(failure_actions["server_error"]["name"], "server_error")
        self.assertEqual(failure_actions["server_error"]["retryAfter"], 2)
        self.assertEqual(failure_actions["server_error"]["retryLimit"], 3)
        self.assertEqual(
            failure_actions["server_error"]["criteria"][0]["condition"],
            "$statusCode >= 500",
        )

        # Check default_retry action
        self.assertIn("default_retry", failure_actions)
        self.assertEqual(failure_actions["default_retry"]["type"], "retry")
        self.assertEqual(failure_actions["default_retry"]["name"], "default_retry")
        self.assertEqual(failure_actions["default_retry"]["retryAfter"], 1)
        self.assertEqual(failure_actions["default_retry"]["retryLimit"], 3)

        # Check default_failure action
        self.assertIn("default_failure", failure_actions)
        self.assertEqual(failure_actions["default_failure"]["type"], "end")
        self.assertEqual(failure_actions["default_failure"]["name"], "default_failure")


if __name__ == "__main__":
    unittest.main()
