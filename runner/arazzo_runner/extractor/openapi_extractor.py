#!/usr/bin/env python3
"""
OpenAPI Parameter and Response Extractor for Arazzo Runner

This module provides functionality to extract input parameters and output schemas
from an OpenAPI specification for a given API operation.
"""

import copy
import logging
import re
from typing import Any

import jsonpointer

from arazzo_runner.auth.models import SecurityOption
from arazzo_runner.executor.operation_finder import OperationFinder

# Configure logging (using the same logger as operation_finder for consistency)
logger = logging.getLogger("arazzo_runner.extractor")


def _format_security_options_to_dict_list(
    security_options_list: list[SecurityOption],
    operation_info: dict[str, Any],  # For logging context
) -> list[dict[str, list[str]]]:
    """
    Converts a list of SecurityOption objects into a list of dictionaries
    representing OpenAPI security requirements.

    Args:
        security_options_list: The list of SecurityOption objects.
        operation_info: The operation details dictionary for logging context.

    Returns:
        A list of dictionaries, where each dictionary represents an OR security option,
        and its key-value pairs represent ANDed security schemes.
    """
    formatted_requirements = []
    if not security_options_list:
        return formatted_requirements

    for sec_opt in security_options_list:
        current_option_dict = {}
        if sec_opt.requirements:  # Check if the list is not None and not empty
            for sec_req in sec_opt.requirements:
                try:
                    current_option_dict[sec_req.scheme_name] = sec_req.scopes
                except AttributeError as e:
                    op_path = operation_info.get("path", "unknown_path")
                    op_method = operation_info.get("http_method", "unknown_method").upper()
                    logger.warning(
                        f"Missing attributes on SecurityRequirement object for operation {op_method} {op_path}. Error: {e}"
                    )

        # Handle OpenAPI's concept of an empty security requirement object {},
        # (optional authentication), represented by an empty list of requirements.
        if sec_opt.requirements == []:  # Explicitly check for an empty list
            formatted_requirements.append({})
        elif current_option_dict:  # Add if populated from non-empty requirements
            formatted_requirements.append(current_option_dict)

    return formatted_requirements


def _schema_brief(schema: Any) -> str:
    """Return a short, non-recursive description of a schema to keep logs lightweight."""
    try:
        if isinstance(schema, dict):
            if "$ref" in schema and len(schema) == 1:
                return f"$ref({schema['$ref']})"
            t = schema.get("type")
            keys = list(schema.keys())
            return f"dict(type={t}, keys={keys[:6]}{'...' if len(keys)>6 else ''})"
        if isinstance(schema, list):
            return f"list(len={len(schema)})"
        return f"{type(schema).__name__}"
    except Exception:
        return "<unprintable schema>"


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """
    Resolve a single JSON Pointer ``$ref`` to its target object.

    Scope and behavior:
    - Low-level dereference for any OpenAPI object (Parameter, Response, Schema, etc.).
    - Resolves only the given pointer; it does NOT recursively walk nested structures.
    - Does NOT perform sibling-merge semantics. Sibling merge is schema-specific and
      intentionally omitted here to avoid corrupting non-schema objects.
    - Cycle-safe: if a direct/indirect cycle is detected along the current path, returns
      a placeholder ``{"$ref": ref}`` to break recursion.
    - Uses a small per-call memoization cache to avoid redundant pointer resolution.
    """
    logger.debug(f"Attempting to resolve ref: {ref}")

    # Use function attributes for per-call caches without changing the signature.
    # These are reset on each top-level invocation.
    def _resolve_with_state(
        spec: dict[str, Any], ref: str, stack: set[str], cache: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        # Ensure the ref starts with '#/' as expected for internal refs
        if not ref.startswith("#/"):
            raise ValueError(
                f"Invalid or unsupported $ref format: {ref}. Only internal refs starting with '#/' are supported."
            )

        # Return from cache when available
        if ref in cache:
            return copy.deepcopy(cache[ref])

        # Detect circular references along the current resolution path
        if ref in stack:
            logger.debug(
                f"Circular $ref detected while resolving {ref}. Returning non-expanded $ref to break the cycle."
            )
            # Do not expand further; return the $ref dict as a safe placeholder
            return {"$ref": ref}

        stack.add(ref)
        try:
            resolved_data = jsonpointer.resolve_pointer(spec, ref[1:])

            # If the resolved item is itself a $ref wrapper, resolve it with the same state
            if isinstance(resolved_data, dict) and "$ref" in resolved_data:
                inner_ref = resolved_data["$ref"]
                result = _resolve_with_state(spec, inner_ref, stack, cache)
            else:
                if not isinstance(resolved_data, dict):
                    logger.warning(
                        f"Resolved $ref '{ref}' is not a dictionary, returning empty dict."
                    )
                    result = {}
                else:
                    result = copy.deepcopy(resolved_data)

            # Memoize before returning
            cache[ref] = result
            return copy.deepcopy(result)
        except jsonpointer.JsonPointerException as e:
            logger.error(f"Could not resolve reference '{ref}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during $ref resolution for {ref}: {e}")
            raise
        finally:
            # Ensure current ref is popped even on exceptions
            stack.discard(ref)

    try:
        return _resolve_with_state(spec, ref, stack=set(), cache={})
    except ValueError as e:
        logger.error(f"Invalid or unsupported $ref format: {e}")
        raise


def merge_json_schemas(
    target: dict[str, Any], source: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Merge two JSON Schema objects following JSON Schema Draft 4/5 and 2020-12 specifications.

    This function handles the merging of two schema objects, including:
    - Boolean JSON Schemas (true/false) with OpenAPI 3.1.x compatibility
    - Properties merging with recursive handling
    - Required fields consolidation
    - Type keyword merging
    - Enum merging
    - Items, contains, contentSchema merging
    - Other schema keywords

    For OpenAPI 3.1.x compatibility, Boolean schemas are converted to proper
    schema object representations before merging to ensure compatibility with
    higher-order code that expects schema objects.

    Args:
        target: The target schema object to merge into
        source: The source schema object to merge from
        config: Optional configuration for merging behavior

    Returns:
        The merged schema object
    """
    if config is None:
        config = {}

    # Handle Boolean JSON Schemas - Booleans take precedence
    if target is True or target is False:
        return target
    if source is True or source is False:
        return source

    # Handle non-object types
    if not isinstance(target, dict):
        return source
    if not isinstance(source, dict):
        return target

    # If either schema has additionalProperties: false, don't merge - return the one with the constraint
    # This prevents adding properties to a schema that explicitly forbids them
    if target.get("additionalProperties") is False:
        return target
    if source.get("additionalProperties") is False:
        return source

    # Start with source, then overlay target (target takes precedence)
    merged = {**source, **target}

    # Merge type keyword
    if "type" in source and "type" in target:
        source_type = source["type"]
        target_type = target["type"]

        if isinstance(source_type, str | list) and isinstance(target_type, str | list):
            # Convert to lists for easier handling
            source_types = source_type if isinstance(source_type, list) else [source_type]
            target_types = target_type if isinstance(target_type, list) else [target_type]

            # Combine and deduplicate
            combined_types = list(set(source_types + target_types))
            merged["type"] = combined_types[0] if len(combined_types) == 1 else combined_types

    # Merge required keyword
    if "required" in source and "required" in target:
        source_required = source["required"] if isinstance(source["required"], list) else []
        target_required = target["required"] if isinstance(target["required"], list) else []
        merged["required"] = list(set(source_required + target_required))

    # Merge properties keyword
    if "properties" in source and "properties" in target:
        source_props = source["properties"] if isinstance(source["properties"], dict) else {}
        target_props = target["properties"] if isinstance(target["properties"], dict) else {}

        all_property_names = set(source_props.keys()) | set(target_props.keys())
        merged["properties"] = {}

        for prop_name in all_property_names:
            source_prop = source_props.get(prop_name, {})
            target_prop = target_props.get(prop_name, {})

            # Merge properties recursively
            merged["properties"][prop_name] = merge_json_schemas(target_prop, source_prop, config)

    # Merge items keyword
    if "items" in source and "items" in target:
        source_items = source["items"]
        target_items = target["items"]

        if isinstance(source_items, dict) and isinstance(target_items, dict):
            merged["items"] = merge_json_schemas(target_items, source_items, config)
        else:
            # If one is not a dict, use the target (which takes precedence)
            merged["items"] = target_items

    # Merge contains keyword
    if "contains" in source and "contains" in target:
        source_contains = source["contains"]
        target_contains = target["contains"]

        if isinstance(source_contains, dict) and isinstance(target_contains, dict):
            merged["contains"] = merge_json_schemas(target_contains, source_contains, config)
        else:
            merged["contains"] = target_contains

    # Merge contentSchema keyword
    if "contentSchema" in source and "contentSchema" in target:
        source_content = source["contentSchema"]
        target_content = target["contentSchema"]

        if isinstance(source_content, dict) and isinstance(target_content, dict):
            merged["contentSchema"] = merge_json_schemas(target_content, source_content, config)
        else:
            merged["contentSchema"] = target_content

    # Merge enum keyword
    if "enum" in source and "enum" in target:
        source_enum = source["enum"] if isinstance(source["enum"], list) else []
        target_enum = target["enum"] if isinstance(target["enum"], list) else []
        merged["enum"] = list(set(source_enum + target_enum))

    return merged


def _convert_booleans_to_dict_representation(schema: Any) -> Any:
    """
    Convert Boolean JSON Schemas to dict-based representations for agents.

    This is the final step before schemas are shown to agents, converting:
    - True -> {} (empty schema that accepts anything)
    - False -> {"not": {}} (schema that rejects everything)

    Processes:
    1. Direct True/False schemas
    2. oneOf/anyOf arrays at the top level (only direct boolean items)

    Args:
        schema: The schema to process

    Returns:
        The schema with Boolean values converted to dict-based representations
    """

    def map_boolean_schema_to_dict_representation(schema: Any) -> Any:
        if schema is True:
            return {}
        elif schema is False:
            return {"not": {}}
        else:
            return schema

    if isinstance(schema, bool):
        return map_boolean_schema_to_dict_representation(schema)

    # Handle dict schemas with oneOf/anyOf arrays
    if isinstance(schema, dict):
        result = schema.copy()

        # Handle oneOf/anyOf arrays at the top level
        for array_key in ["oneOf", "anyOf"]:
            if array_key in schema and isinstance(schema[array_key], list):
                result[array_key] = []
                for item in schema[array_key]:
                    if isinstance(item, bool):
                        result[array_key].append(map_boolean_schema_to_dict_representation(item))
                    else:
                        result[array_key].append(item)  # Keep non-boolean items as-is

        return result
    else:
        return schema


def fold_all_of(schema: Any) -> Any:
    """
    Recursively fold allOf arrays into single schema objects by merging all allOf items.

    This function takes a schema that may contain allOf arrays and folds them
    into single schemas without allOf keywords, using merge_json_schemas.
    It processes the schema recursively to handle nested allOf arrays.

    Note: Raw Boolean values (True/False) are not expected here as they are
    converted to proper schema objects in _resolve_schema_refs via _convert_boolean_schema.

    Args:
        schema: The schema object that may contain allOf arrays

    Returns:
        The schema with allOf arrays folded into single objects
    """
    if isinstance(schema, dict):
        # First, recursively process all values in the schema
        processed_schema = {k: fold_all_of(v) for k, v in schema.items()}

        # If no allOf, return the processed schema
        if "allOf" not in processed_schema:
            return processed_schema

        all_of_items = processed_schema["allOf"]
        if not isinstance(all_of_items, list) or not all_of_items:
            return processed_schema

        # Start with an empty schema
        merged_schema = {}

        # Merge all allOf items
        for item in all_of_items:
            if isinstance(item, dict):
                merged_schema = merge_json_schemas(merged_schema, item)
            elif item is True or item is False:
                # Handle Boolean JSON Schemas - they take precedence
                merged_schema = item

        # Remove the allOf keyword and merge with any other properties in the original schema
        schema_without_allof = {k: v for k, v in processed_schema.items() if k != "allOf"}
        result = merge_json_schemas(merged_schema, schema_without_allof)

        return result
    elif isinstance(schema, list):
        # Process each item in the list
        return [fold_all_of(item) for item in schema]
    else:
        # Return primitive types as-is
        return schema


def _resolve_schema_refs(
    schema_part: Any,
    full_spec: dict[str, Any],
    visited_refs: set[str] | None = None,
    cache: dict[str, Any] | None = None,
) -> Any:
    """
    Resolve schema references without sibling merging.

    This function only handles reference resolution and cycle elimination,
    without merging sibling properties. This allows for clean separation of
    concerns where sibling merging can be handled in a separate pass.

    Handles Boolean JSON Schemas (True/False) as identity functions for OpenAPI 3.1.x
    compatibility, where schemas can be represented as boolean values.

    Args:
        schema_part: The schema fragment to resolve
        full_spec: The full OpenAPI specification
        visited_refs: Set of visited references for cycle detection
        cache: Memoization cache for resolved references

    Returns:
        The schema with references resolved but siblings not merged
    """
    stack = visited_refs if visited_refs is not None else set()
    memo = cache if cache is not None else {}

    # Handle Boolean JSON Schemas (OpenAPI 3.1.x compatibility)
    if schema_part is True or schema_part is False:
        return schema_part

    # Primitives pass through
    if not isinstance(schema_part, dict | list):
        return schema_part

    if isinstance(schema_part, dict):
        if "$ref" in schema_part:
            ref = schema_part["$ref"]
            if ref in memo:
                result = memo[ref]
            else:
                if ref in stack:
                    logger.debug(
                        f"Circular reference detected for '{ref}'. Returning $ref placeholder."
                    )
                    return {"$ref": ref}
                stack.add(ref)
                try:
                    target = jsonpointer.resolve_pointer(full_spec, ref[1:])
                    if not isinstance(target, dict | list):
                        logger.warning(
                            f"Resolved $ref '{ref}' is not a dict/list. Returning empty dict."
                        )
                        result = {}
                    else:
                        # Provisional entry breaks indirect cycles
                        memo[ref] = {"$ref": ref}
                        result = _resolve_schema_refs(target, full_spec, stack, memo)
                        memo[ref] = result
                except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                    logger.warning(f"Could not resolve nested $ref '{ref}': {e}")
                    result = {"$ref": ref}
                finally:
                    stack.discard(ref)

            # Return the resolved result without merging siblings
            return result

        # Regular dict: resolve entries
        return {k: _resolve_schema_refs(v, full_spec, stack, memo) for k, v in schema_part.items()}

    # List: resolve items
    return [_resolve_schema_refs(item, full_spec, stack, memo) for item in schema_part]


def merge_siblings(schema: Any, original_schema: Any) -> Any:
    """
    Merge sibling properties with resolved $ref schemas using merge_json_schemas.

    This function handles the case where a schema object contains both a $ref
    and additional properties at the same level. It surfaces sibling fields as
    objects and combines them using the established merge_json_schemas algorithm.

    Args:
        schema: The schema with resolved references
        original_schema: The original schema before reference resolution

    Returns:
        The schema with sibling properties merged using merge_json_schemas
    """
    if isinstance(schema, dict) and isinstance(original_schema, dict):
        # Check if the original had a $ref with siblings
        if "$ref" in original_schema and len(original_schema) > 1:
            # This was a $ref with siblings - extract siblings and merge
            siblings = {k: v for k, v in original_schema.items() if k != "$ref"}

            # Use merge_json_schemas to combine resolved schema with siblings
            return merge_json_schemas(schema, siblings)
        else:
            # No $ref with siblings, return resolved schema as-is
            return schema
    else:
        # Return the resolved schema as-is
        return schema


def resolve_schema(
    schema_part: Any,
    full_spec: dict[str, Any],
    visited_refs: set[str] | None = None,
    cache: dict[str, Any] | None = None,
) -> Any:
    """
    Three-pass schema resolution with OpenAPI 3.0.x and 3.1.x compatibility:
    1. Reference resolution with cycle elimination (without sibling merging)
    2. Sibling merging using merge_json_schemas for proper schema merging
    3. allOf folding using merge_json_schemas

    This function implements the cleanest separation of concerns approach
    where each pass handles a single responsibility. It supports both:
    - OpenAPI 3.0.x: Reference Objects are replaced by referenced Schema Objects
    - OpenAPI 3.1.x: Schema Objects can reference other Schema Objects with proper
      merging using the established schema merging algorithm

    Handles Boolean JSON Schemas (True/False) by converting them to proper
    schema object representations for compatibility with higher-order code.

    Args:
        schema_part: The schema fragment to resolve
        full_spec: The full OpenAPI specification
        visited_refs: Set of visited references for cycle detection
        cache: Memoization cache for resolved references

    Returns:
        The fully resolved schema with all transformations applied
    """
    # Pass 1: Reference resolution with cycle elimination (without sibling merging)
    resolved_schema = _resolve_schema_refs(schema_part, full_spec, visited_refs, cache)

    # Pass 2: Sibling merging
    merged_schema = merge_siblings(resolved_schema, schema_part)

    # Pass 3: allOf folding
    result = fold_all_of(merged_schema)

    # Final step: Convert Boolean schemas to dict-based representations for agents
    # Note: if the schema is a boolean schema, an empty dict will be shown to the agent, as it is not a schema of type: object.
    # If this becomes an issue, a future fix can be implemented to alter this behaviour.
    return _convert_booleans_to_dict_representation(result)


def _extract_media_type_schema(body_content: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Extract schema from request/response body content, prioritizing JSON over form-encoded.

    This function looks for supported media types in the body_content dictionary:
    1. First tries to find any media type that starts with "application/json"
    2. If no JSON content type found, looks for "application/x-www-form-urlencoded"
    3. Returns the schema from the first matching media type, or None if none found

    This handles media types with parameters like "application/json;q=0.7" by matching
    the prefix rather than requiring exact key matches.

    Args:
        body_content: Dictionary mapping media types to their schemas

    Returns:
        The schema object from the first supported media type, or None if none found
    """
    if not isinstance(body_content, dict):
        logger.debug("Body schema must be a dictionary.")
        return None

    if len(body_content.keys()) == 0:
        logger.debug("No media type definitions found in the body schema.")
        return None

    for prefix in ("application/json", "application/x-www-form-urlencoded"):
        for media_type, value in body_content.items():
            if media_type.startswith(prefix):
                logger.debug(f"Found {prefix} media type in the body schema.")
                return value.get("schema")

    logger.debug("No supported media type found in the body schema.")
    return None


def extract_operation_io(
    spec: dict[str, Any],
    http_path: str,
    http_method: str,
    input_max_depth: int | None = None,
    output_max_depth: int | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Finds the specified operation within the spec and extracts input parameters
    structured as an OpenAPI object schema and the full schema for the success
    (200 or 201) response.

    Args:
        spec: The full OpenAPI specification dictionary.
        http_path: The HTTP path of the target operation (e.g., '/users/{id}').
        http_method: The HTTP method of the target operation (e.g., 'get', 'post').
        input_max_depth: If set, limits the depth of the input structure.
        output_max_depth: If set, limits the depth of the output structure.

    Returns:
        A dictionary containing 'inputs', 'outputs', and 'security_requirements'.
        Returns the full, unsimplified dict structure if both max depth arguments are None.
        'inputs' is structured like an OpenAPI schema object:
            {'type': 'object', 'properties': {param_name: {param_schema_or_simple_type}, ...}}
            Non-body params map to {'type': openapi_type_string}.
            The JSON request body schema is included under the 'body' key if present.
        'outputs' contains the full resolved schema for the 200 JSON response.
        'security_requirements' contains the security requirements for the operation.

        Example:
        {
            "inputs": {
                "type": "object",
                "properties": {
                    "userId": {"type": "integer"},   # Non-body param
                    "limit": {"type": "integer"},
                    "body": {                     # Full resolved schema for JSON request body
                        "type": "object",
                        "properties": {
                            "items": {"type": "array", "items": {"type": "string"}},
                            "customer_notes": {"type": "string"}
                        },
                        "required": ["items"]
                    }
                }
            },
            "outputs": { # Full resolved schema for 200 JSON response
                 "type": "object",
                 "properties": {
                      "id": {"type": "string", "format": "uuid"},
                      "status": {"type": "string", "enum": ["pending", "shipped"]}
                 }
            },
            "security_requirements": [
                # List of SecurityOption objects
            ]
        }
    """
    # Find the operation first using OperationFinder
    # Wrap the spec for OperationFinder
    source_name = spec.get("info", {}).get("title", "default_spec")
    source_descriptions = {source_name: spec}
    finder = OperationFinder(source_descriptions)
    operation_info = finder.find_by_http_path_and_method(http_path, http_method.lower())

    if not operation_info:
        logger.warning(f"Operation {http_method.upper()} {http_path} not found in the spec.")
        # Return early if operation not found
        return {"inputs": {}, "outputs": {}, "security_requirements": []}

    # Initialize with new structure for inputs
    extracted_details: dict[str, Any] = {
        "inputs": {"type": "object", "properties": {}, "required": []},
        "outputs": {},
        "security_requirements": [],
    }
    operation = operation_info.get("operation")
    if not operation or not isinstance(operation, dict):
        logger.warning("Operation object missing or invalid in operation_info.")
        return extracted_details

    # Extract security requirements using OperationFinder
    security_options_list: list[SecurityOption] = finder.extract_security_requirements(
        operation_info
    )

    extracted_details["security_requirements"] = _format_security_options_to_dict_list(
        security_options_list, operation_info
    )

    all_parameters = []
    seen_params = set()

    # Check for path-level parameters first
    path_item_ref = f"#/paths/{operation_info.get('path', '').lstrip('/')}"
    try:
        escaped_path = (
            operation_info.get("path", "").lstrip("/").replace("~", "~0").replace("/", "~1")
        )
        path_item_ref = f"#/paths/{escaped_path}"
        path_item = jsonpointer.resolve_pointer(spec, path_item_ref[1:])
        if path_item and isinstance(path_item, dict) and "parameters" in path_item:
            for param in path_item["parameters"]:
                try:
                    resolved_param = param
                    if "$ref" in param:
                        resolved_param = _resolve_ref(spec, param["$ref"])
                    param_key = (resolved_param.get("name"), resolved_param.get("in"))
                    if param_key not in seen_params:
                        all_parameters.append(resolved_param)
                        seen_params.add(param_key)
                except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                    logger.warning(
                        f"Skipping path-level parameter due to resolution/format error: {e}"
                    )
    except jsonpointer.JsonPointerException:
        logger.debug(f"Could not find or resolve path item: {path_item_ref}")

    # Add/override with operation-level parameters
    if "parameters" in operation:
        for param in operation["parameters"]:
            try:
                resolved_param = param
                if "$ref" in param:
                    resolved_param = _resolve_ref(spec, param["$ref"])
                param_key = (resolved_param.get("name"), resolved_param.get("in"))
                existing_index = next(
                    (
                        i
                        for i, p in enumerate(all_parameters)
                        if (p.get("name"), p.get("in")) == param_key
                    ),
                    None,
                )
                if existing_index is not None:
                    all_parameters[existing_index] = resolved_param
                elif param_key not in seen_params:
                    all_parameters.append(resolved_param)
                    seen_params.add(param_key)
            except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                logger.warning(
                    f"Skipping operation-level parameter due to resolution/format error: {e}"
                )

    # --- Ensure all URL path parameters are present and required ---
    # Find all {param} in the http_path
    url_param_names = re.findall(r"{([^}/]+)}", http_path)
    for url_param in url_param_names:
        param_key = (url_param, "path")
        if param_key not in seen_params:
            all_parameters.append(
                {"name": url_param, "in": "path", "required": True, "schema": {"type": "string"}}
            )
            seen_params.add(param_key)
    # --- End ensure URL params ---

    # Process collected parameters into simplified inputs
    for param in all_parameters:
        param_name = param.get("name")
        param_in = param.get("in")
        param_schema = param.get("schema")
        if param_name and param_in != "body":  # Body handled separately
            if not param_schema:
                logger.warning(
                    f"Parameter '{param_name}' in '{param_in}' is missing schema, mapping type to 'any'"
                )
            else:
                # Resolve schema ref if present
                if isinstance(param_schema, dict) and "$ref" in param_schema:
                    # Defer full resolution to resolve_schema to properly handle cycles, siblings, and allOf
                    try:
                        param_schema = resolve_schema(param_schema, spec)
                    except Exception as ref_e:
                        logger.warning(
                            f"Could not resolve schema $ref for parameter '{param_name}': {ref_e}"
                        )
                        param_schema = {}  # Fallback to empty schema
            openapi_type = "string"  # Default OpenAPI type
            if isinstance(param_schema, dict):
                oapi_type_from_schema = param_schema.get("type")
                # Map to basic OpenAPI types
                if oapi_type_from_schema in [
                    "string",
                    "integer",
                    "number",
                    "boolean",
                    "array",
                    "object",
                ]:
                    openapi_type = oapi_type_from_schema
                # TODO: More nuanced mapping (e.g., number format to float/double?)?

            # Add to properties as { 'type': 'openapi_type_string' }
            # Required status will be tracked in the top-level 'required' list
            is_required = param.get("required", False)  # Default to false if not present
            param_input = {"type": openapi_type, "schema": param_schema or {}}
            # Add description if it exists
            param_description = param.get("description")
            if param_description:
                param_input["description"] = param_description
            extracted_details["inputs"]["properties"][param_name] = param_input
            if is_required:
                # Add to top-level required list if not already present
                if param_name not in extracted_details["inputs"]["required"]:
                    extracted_details["inputs"]["required"].append(param_name)

    # Process Request Body for inputs
    if "requestBody" in operation:
        try:
            request_body = operation["requestBody"]
            if "$ref" in request_body:
                # Resolve requestBody schema using three-pass resolver with cycles, siblings, and allOf.
                try:
                    request_body = resolve_schema(request_body, spec)
                except Exception as e:
                    # Continue with execution even if schema could not be fully resolved
                    logger.warning(f"Could not resolve requestBody: {e}")

            # Check for application/json or application/x-www-form-urlencoded content in the request body
            body_content = request_body.get("content", {})

            body_schema = _extract_media_type_schema(body_content)

            if body_schema is not None:
                # Let the recursive resolver handle any $ref and cycles

                # Recursively resolve nested refs within the body schema with three-pass resolution
                fully_resolved_body_schema = resolve_schema(body_schema, spec)
                # --- Flatten body properties into inputs ---
                if (
                    isinstance(fully_resolved_body_schema, dict)
                    and fully_resolved_body_schema.get("type") == "object"
                ):
                    body_properties = fully_resolved_body_schema.get("properties", {})
                    for prop_name, prop_schema in body_properties.items():
                        if prop_name in extracted_details["inputs"]["properties"]:
                            # Handle potential name collisions (e.g., param 'id' and body field 'id')
                            # Current approach: Body property overwrites if name collides. Log warning.
                            logger.warning(
                                f"Body property '{prop_name}' overwrites existing parameter with the same name."
                            )
                        extracted_details["inputs"]["properties"][prop_name] = prop_schema

                    # Add required body properties to the main 'required' list
                    body_required = fully_resolved_body_schema.get("required", [])
                    for req_prop_name in body_required:
                        if req_prop_name not in extracted_details["inputs"]["required"]:
                            extracted_details["inputs"]["required"].append(req_prop_name)
                elif isinstance(fully_resolved_body_schema, dict) and (
                    any(
                        structure_type in fully_resolved_body_schema
                        for structure_type in ["oneOf", "anyOf"]
                    )
                ):
                    for structure_type in ["oneOf", "anyOf"]:
                        if structure_type in fully_resolved_body_schema:
                            # Copy regular input params into each oneOf/anyOf entry and perform sibling merge
                            regular_params = extracted_details["inputs"]["properties"].copy()

                            # Process each option in the oneOf/anyOf array
                            extracted_properties = []
                            for option in fully_resolved_body_schema[structure_type]:
                                # Skip raw array and string request bodies - not yet supported
                                # Boolean schemas are also skipped in multiple option scenarios for the time being
                                if (
                                    option.get("type") in ["array", "string"]
                                    or "properties" not in option
                                ):
                                    continue

                                # Create base object with regular input properties
                                base_object = {"type": "object", "properties": regular_params}

                                # Use merge_json_schemas to merge the option into the base object
                                merged_option = merge_json_schemas(base_object, option)

                                # Extract individual properties from the merged option
                                if "properties" in merged_option:
                                    # Create a flat dict with all properties
                                    flat_properties = {}
                                    required_fields = set(merged_option.get("required", []))

                                    for prop_name, prop_schema in merged_option[
                                        "properties"
                                    ].items():
                                        flat_properties[prop_name] = prop_schema
                                        # Add required field if the property is required
                                        if prop_name in required_fields:
                                            flat_properties[prop_name]["required"] = True

                                    extracted_properties.append(flat_properties)

                            # Store the extracted properties array in inputs properties
                            extracted_details["inputs"]["properties"] = extracted_properties
                            extracted_details["inputs"]["strategy"] = structure_type
                            break
                else:
                    # If body is not an object (e.g., array, primitive) or has no properties, don't flatten.
                    # Log a warning as we are not adding it under 'body' key either per the requirement.
                    logger.warning(
                        f"Request body for {http_method.upper()} {http_path} is not an object with properties. Skipping flattening."
                    )
                # --- End flatten ---

                # Removed code that added the schema under 'body'
                # Removed code that checked 'required' on the nested 'body' object

        except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
            logger.warning(f"Skipping request body processing due to error: {e}")

    # Process 200 or 201 Response for outputs
    if "responses" in operation:
        responses = operation.get("responses", {})
        # Prioritize 200, fallback to 201 for success output schema
        success_response = responses.get("200") or responses.get("201")
        if success_response:
            try:
                resolved_response = success_response
                if isinstance(success_response, dict) and "$ref" in success_response:
                    # Resolve response object safely with three-pass schema resolver
                    resolved_response = resolve_schema(success_response, spec)

                # Check for application/json or application/x-www-form-urlencoded content in the resolved successful response
                response_content = resolved_response.get("content", {})

                response_schema = _extract_media_type_schema(response_content)

                if response_schema is not None:
                    # Recursively resolve nested refs within the response schema
                    logger.debug(
                        f"Output schema BEFORE recursive resolve: {_schema_brief(response_schema)}"
                    )
                    fully_resolved_output_schema = resolve_schema(response_schema, spec)
                    logger.debug(
                        f"Output schema AFTER recursive resolve: {_schema_brief(fully_resolved_output_schema)}"
                    )
                    extracted_details["outputs"] = fully_resolved_output_schema

            except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                logger.warning(f"Skipping success response processing due to error: {e}")
        else:
            logger.debug("No '200' or '201' response found for this operation.")

    # --- Limit output depth (conditionally) ---
    if input_max_depth is not None:
        if isinstance(extracted_details.get("inputs"), dict | list):
            extracted_details["inputs"] = _limit_dict_depth(
                extracted_details["inputs"], input_max_depth
            )
    if output_max_depth is not None:
        if isinstance(extracted_details.get("outputs"), dict | list):
            extracted_details["outputs"] = _limit_dict_depth(
                extracted_details["outputs"], output_max_depth
            )

    # If both max depths are None, return the full, unsimplified details
    return extracted_details


def _limit_dict_depth(
    data: dict | list | Any, max_depth: int, current_depth: int = 0
) -> dict | list | Any:
    """Recursively limits the depth of a dictionary or list structure."""

    if isinstance(data, dict):
        if current_depth >= max_depth:
            return data.get("type", "object")  # Limit hit for dict
        else:
            # Recurse into dict
            limited_dict = {}
            for key, value in data.items():
                # Special case to preserve enum lists
                if key == "enum" and isinstance(value, list):
                    limited_dict[key] = value
                else:
                    limited_dict[key] = _limit_dict_depth(value, max_depth, current_depth + 1)
            return limited_dict
    elif isinstance(data, list):
        if current_depth >= max_depth:
            return "array"  # Limit hit for list
        else:
            # Recurse into list
            limited_list = []
            for item in data:
                limited_list.append(_limit_dict_depth(item, max_depth, current_depth + 1))
            return limited_list
    else:
        # It's a primitive, return the value itself regardless of depth
        return data
