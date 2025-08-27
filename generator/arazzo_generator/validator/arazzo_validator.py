"""Arazzo specification validator module."""

from pathlib import Path
from typing import Any

import jsonschema
import requests
import yaml

from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)


class ArazzoValidator:
    """Validator for Arazzo specifications.

    This class is responsible for validating generated Arazzo specifications
    against the Arazzo schema.
    """

    ARAZZO_SCHEMA_URL = (
        "https://github.com/OAI/Arazzo-Specification/blob/main/schemas/v1.0/schema.json"
    )
    ARAZZO_SCHEMA_VERSION = "1.0.1"  # Current schema version
    ARAZZO_SCHEMA_PATH = str(
        Path(__file__).parent / "arazzo_schema" / ARAZZO_SCHEMA_VERSION / "arazzo-schema.yaml"
    )

    def __init__(self):
        """Initialize the Arazzo validator."""
        self.schema = None

    def load_schema(self) -> dict[str, Any]:
        """Load the Arazzo schema.

        Returns:
            The Arazzo schema as a dictionary.

        Raises:
            ValueError: If the schema cannot be loaded.
        """
        if self.schema:
            return self.schema

        # List of schema versions to try, in order of preference
        schema_versions = [self.ARAZZO_SCHEMA_VERSION, "1.0.0", "1.0"]

        try:
            # Try to load the schema from the versioned directory structure
            for version in schema_versions:
                # Try the validator directory first
                schema_path = (
                    Path(__file__).parent / "arazzo_schema" / version / "arazzo-schema.yaml"
                )
                if schema_path.exists():
                    with open(schema_path) as f:
                        self.schema = yaml.safe_load(f)
                    logger.info(f"Loaded Arazzo schema version {version} from validator directory")
                    return self.schema

                # Then try the design directory
                design_path = (
                    Path(__file__).parents[3]
                    / "design"
                    / "arazzo_schema"
                    / version
                    / "arazzo-schema.yaml"
                )
                if design_path.exists():
                    with open(design_path) as f:
                        self.schema = yaml.safe_load(f)
                    logger.info(f"Loaded Arazzo schema version {version} from design directory")
                    return self.schema

            # If versioned schemas are not found, try the legacy non-versioned path
            legacy_path = Path(__file__).parents[3] / "design" / "arazzo-schema.yaml"
            if legacy_path.exists():
                with open(legacy_path) as f:
                    self.schema = yaml.safe_load(f)
                logger.info("Loaded Arazzo schema from legacy path")
                return self.schema

        except Exception as e:
            logger.warning(f"Failed to load Arazzo schema from local files: {e}")

        try:
            # Fallback: Try to load the schema from the URL
            response = requests.get(self.ARAZZO_SCHEMA_URL, timeout=100)
            response.raise_for_status()
            self.schema = response.json()
            logger.info("Loaded Arazzo schema from URL")
            return self.schema
        except Exception as e:
            logger.warning(f"Failed to load Arazzo schema from URL: {e}")
            raise ValueError("Failed to load Arazzo schema from local files or URL") from e

    def validate(self, arazzo_spec: dict[str, Any] | str) -> bool:
        """Validate an Arazzo specification against the schema.

        Args:
            arazzo_spec: The Arazzo specification to validate, as a dictionary or YAML string.

        Returns:
            True if the specification is valid, False otherwise.
        """
        # Load the schema if it hasn't been loaded yet
        if not self.schema:
            self.load_schema()

        # Convert string to dictionary if necessary
        if isinstance(arazzo_spec, str):
            try:
                arazzo_spec = yaml.safe_load(arazzo_spec)
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse Arazzo spec as YAML: {e}")
                return False

        # Validate the specification
        try:
            jsonschema.validate(instance=arazzo_spec, schema=self.schema)
            logger.info("Arazzo specification validation successful")
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Arazzo specification validation failed: {e}")
            return False

    def get_validation_errors(self, arazzo_spec: dict[str, Any] | str) -> list[str]:
        """Get validation errors for an Arazzo specification.

        Args:
            arazzo_spec: The Arazzo specification to validate, as a dictionary or YAML string.

        Returns:
            A list of validation error messages.
        """
        # Load the schema if it hasn't been loaded yet
        if not self.schema:
            self.load_schema()

        # Convert string to dictionary if necessary
        if isinstance(arazzo_spec, str):
            try:
                arazzo_spec = yaml.safe_load(arazzo_spec)
            except yaml.YAMLError as e:
                return [f"Failed to parse Arazzo spec as YAML: {e}"]

        # Validate the specification and collect errors
        validator = jsonschema.Draft202012Validator(self.schema)
        errors = list(validator.iter_errors(arazzo_spec))

        # Format error messages
        error_messages = []
        for error in errors:
            path = "/".join(str(path_item) for path_item in error.path)
            message = f"{path}: {error.message}"
            error_messages.append(message)

        return error_messages
