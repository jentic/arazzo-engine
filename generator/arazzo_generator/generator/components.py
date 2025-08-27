"""Components for Arazzo specifications."""

from typing import Any

from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)


class ArazzoComponentsBuilder:
    """Builder for Arazzo components section."""

    @staticmethod
    def create_action(
        action_type: str, name: str, action_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """Create an action (success or failure) that complies with the Arazzo schema.

        Args:
            action_type: The type of action ('end', 'goto', or 'retry').
            name: The name of the action.
            action_definition: Additional properties for the action.

        Returns:
            A valid action object according to the Arazzo schema.
        """
        action = {"name": name, "type": action_type, **action_definition}

        return action

    @staticmethod
    def build_default_components() -> dict[str, Any]:
        """Build the default components section for an Arazzo specification.

        Returns:
            A dictionary containing the components section.
        """
        components = {"components": {}}

        # Define common success actions
        success_actions = {
            "default_success": ArazzoComponentsBuilder.create_action("end", "default_success", {})
        }

        # Define comprehensive failure actions for common error scenarios
        failure_actions = {
            "auth_failure": ArazzoComponentsBuilder.create_action(
                "end",
                "auth_failure",
                {"criteria": [{"condition": "$statusCode == 401"}]},
            ),
            "permission_denied": ArazzoComponentsBuilder.create_action(
                "end",
                "permission_denied",
                {"criteria": [{"condition": "$statusCode == 403"}]},
            ),
            "not_found": ArazzoComponentsBuilder.create_action(
                "end", "not_found", {"criteria": [{"condition": "$statusCode == 404"}]}
            ),
            "server_error": ArazzoComponentsBuilder.create_action(
                "retry",
                "server_error",
                {
                    "retryAfter": 2,
                    "retryLimit": 3,
                    "criteria": [{"condition": "$statusCode >= 500"}],
                },
            ),
            "default_retry": ArazzoComponentsBuilder.create_action(
                "retry",
                "default_retry",
                {
                    "retryAfter": 1,
                    "retryLimit": 3,
                },
            ),
            "default_failure": ArazzoComponentsBuilder.create_action("end", "default_failure", {}),
        }

        components["components"]["successActions"] = success_actions
        components["components"]["failureActions"] = failure_actions

        return components
