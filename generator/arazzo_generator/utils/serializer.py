"""Serialization utilities for Arazzo specifications."""

import json
from typing import Any

import yaml

from arazzo_generator.utils.logging import get_logger
from arazzo_generator.utils.yaml_utils import NoWrapSafeDumper, fix_output_references

logger = get_logger(__name__)


class ArazzoSerializer:
    """Handles serialization of Arazzo specifications to YAML and JSON formats."""

    @staticmethod
    def to_yaml(arazzo_spec: dict[str, Any]) -> str:
        """Convert the Arazzo specification to YAML.

        Args:
            arazzo_spec: The Arazzo specification dictionary

        Returns:
            The Arazzo specification as a YAML string.
        """
        if not arazzo_spec:
            logger.warning("Empty Arazzo specification provided for YAML serialization")
            return ""

        # Generate YAML content
        yaml_str = yaml.dump(
            arazzo_spec,
            Dumper=NoWrapSafeDumper,
            sort_keys=False,
            default_flow_style=False,
            width=10000,  # Set a very large line width to prevent wrapping
        )

        # Fix any broken references
        fixed_yaml = fix_output_references(yaml_str)

        return fixed_yaml

    @staticmethod
    def to_json(arazzo_spec: dict[str, Any]) -> str:
        """Convert the Arazzo specification to JSON.

        Args:
            arazzo_spec: The Arazzo specification dictionary

        Returns:
            The Arazzo specification as a JSON string.
        """
        if not arazzo_spec:
            logger.warning("Empty Arazzo specification provided for JSON serialization")
            return "{}"

        # Generate JSON content with pretty formatting (indent)
        json_str = json.dumps(arazzo_spec, indent=2, ensure_ascii=False)

        return json_str

    @staticmethod
    def get_arazzo_in_target_format(arazzo_spec: dict[str, Any], target_format: str = "json"):
        if target_format == "yaml":
            return ArazzoSerializer.to_yaml(arazzo_spec)
        elif target_format == "json":
            return ArazzoSerializer.to_json(arazzo_spec)
        else:
            raise ValueError(f"Unsupported target format: {target_format}")
