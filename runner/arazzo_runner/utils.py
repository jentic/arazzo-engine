#!/usr/bin/env python3
"""
Utility functions for Runner

This module provides utility functions for Runner, including:
- File loading (JSON/YAML)
- JSON pointer evaluation
- Environment variable sanitization
- Logging helpers
- Deprecated decorator
- Source description loading (local and HTTP)
"""
import json
import logging
import os
import re
import warnings
from typing import Any, Optional, Tuple, Dict

import jsonpointer
import yaml
import requests  # For HTTP client usage in load_source_descriptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("runner-utils")


def load_file(path: str) -> dict[str, Any]:
    """
    Load a JSON or YAML file from a local path.

    Args:
        path: Path to the JSON/YAML file.

    Returns:
        Parsed dictionary from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as JSON/YAML.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path) as f:
        content = f.read()

    try:
        if path.endswith((".yaml", ".yml")):
            return yaml.safe_load(content)
        else:
            return json.loads(content)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse file {path}: {e}")
        raise ValueError(f"Cannot parse file {path}") from e


def load_source_descriptions(
    source_list: list[dict[str, str]],
    base_path: Optional[str] = None,
    arazzo_path: Optional[str] = None,
    http_client=None,
) -> dict[str, Any]:
    """
    Load referenced OpenAPI/JSON/YAML descriptions.

    Args:
        source_list: List of source dictionaries containing 'name' and 'url'.
        base_path: Base path for resolving local paths.
        arazzo_path: Optional path of main document for relative references.
        http_client: Optional HTTP client (e.g., requests) for remote sources.

    Returns:
        Dictionary of loaded source descriptions by name.

    Notes:
        - Handles local files with multiple candidate paths.
        - Handles remote URLs via HTTP client.
    """
    if http_client is None:
        http_client = requests

    source_descriptions = {}

    for source in source_list:
        source_name = source.get("name")
        source_url = source.get("url")

        if not source_name or not source_url:
            continue

        # Handle local file references
        if not source_url.startswith(("http://", "https://")):
            candidate_paths = []
            # 1. Use provided base_path
            if base_path:
                candidate_paths.append(os.path.join(base_path, source_url))
            # 2. Use directory of arazzo_path
            if arazzo_path:
                candidate_paths.append(os.path.join(os.path.dirname(arazzo_path), source_url))
            # 3. Use current working directory
            candidate_paths.append(os.path.join(os.getcwd(), source_url))
            # 4. Special case for runner tool structure
            if "/tools/runner" in os.getcwd():
                candidate_paths.append(os.path.join(os.path.abspath("../.."), source_url))

            # Select first existing path
            source_path = next((p for p in candidate_paths if os.path.exists(p)), None)
            if not source_path:
                raise FileNotFoundError(
                    f"Could not find source file for {source_name}. Tried: {candidate_paths}"
                )

            try:
                # Load the local file
                source_descriptions[source_name] = load_file(source_path)
            except Exception as e:
                logger.error(f"Error loading source {source_name}: {e}")

        # Handle remote URLs
        else:
            try:
                response = http_client.get(source_url)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if "yaml" in content_type or "yml" in content_type:
                    source_descriptions[source_name] = yaml.safe_load(response.text)
                else:
                    source_descriptions[source_name] = response.json()
            except Exception as e:
                logger.error(f"Error loading remote source {source_name}: {e}")

    return source_descriptions


def evaluate_json_pointer(data: dict, pointer_path: str) -> Any | None:
    """
    Evaluate a JSON pointer against the provided data.

    Args:
        data: The data to evaluate the pointer against.
        pointer_path: The JSON pointer path (e.g., "/products/0/name").

    Returns:
        The resolved value, or None if the pointer cannot be resolved.
    """
    if not pointer_path or pointer_path == "/":
        return data
    try:
        return jsonpointer.JsonPointer(pointer_path).resolve(data)
    except (jsonpointer.JsonPointerException, TypeError) as e:
        logger.debug(f"Failed to resolve JSON pointer {pointer_path}: {e}")
        return None


def extract_json_pointer_from_expression(expression: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract JSON pointer from an expression like $response.body#/path/to/value.

    Args:
        expression: The expression containing a JSON pointer.

    Returns:
        A tuple of (container_path, pointer_path) or (None, None) if not valid.
    """
    if not isinstance(expression, str):
        return None, None

    # Form: $response.body#/path/to/value
    match = re.match(r"^\$([a-zA-Z0-9_.]+)#(/.*)", expression)
    if match:
        return match.groups()

    # Form: $response.body.path.to.value
    match = re.match(r"^\$([a-zA-Z0-9_]+)\.([a-zA-Z0-9_.]+)", expression)
    if match and "#" not in expression:
        container, path = match.groups()
        pointer_path = "/" + path.replace(".", "/")
        return container, pointer_path

    return None, None


def sanitize_for_env_var(text: str) -> str:
    """
    Sanitize a string for use in environment variable names.

    Args:
        text: The text to sanitize.

    Returns:
        Sanitized text suitable for environment variables.
    """
    # Convert to uppercase
    sanitized = text.upper()
    # Replace non-alphanumeric characters with underscores
    sanitized = re.sub(r"[^A-Z0-9_]", "_", sanitized)
    # Replace multiple consecutive underscores with a single underscore
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading and trailing underscores
    return sanitized.strip("_")


def create_env_var_name(var_name: str, prefix: Optional[str] = None) -> str:
    """
    Create a standardized environment variable name with an optional prefix.

    Args:
        var_name: The base variable name.
        prefix: Optional prefix (e.g., "MY_API").

    Returns:
        A properly formatted environment variable name.
    """
    parts = [sanitize_for_env_var(var_name)]
    if prefix:
        parts.insert(0, sanitize_for_env_var(prefix))
    return "_".join(parts)


def dump_state(state: Any, label: str = "Execution State") -> None:
    """
    Helper method to dump the current state for debugging.

    Args:
        state: Execution state to dump.
        label: Optional label for the state dump.
    """
    logger.debug(f"=== {label} ===")
    logger.debug(f"Workflow ID: {getattr(state, 'workflow_id', None)}")
    logger.debug(f"Current Step ID: {getattr(state, 'current_step_id', None)}")
    logger.debug(f"Inputs: {getattr(state, 'inputs', None)}")
    step_outputs = getattr(state, 'step_outputs', {})
    logger.debug("Step Outputs:")
    for step_id, outputs in step_outputs.items():
        logger.debug(f"  {step_id}: {outputs}")
    logger.debug(f"Workflow Outputs: {getattr(state, 'workflow_outputs', None)}")
    logger.debug(f"Status: {getattr(state, 'status', None)}")


def deprecated(reason: str):
    """
    Decorator to mark a function as deprecated.

    Args:
        reason: Reason for deprecation.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            warnings.warn(f"{func.__name__} is deprecated: {reason}", DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def set_log_level(level: str):
    """
    Set the log level for runner utilities.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    logger.setLevel(numeric_level)
