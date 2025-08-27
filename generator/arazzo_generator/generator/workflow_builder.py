"""Workflow builder for Arazzo specifications."""

import re
import uuid
from typing import Any

from Levenshtein import distance

from arazzo_generator.utils.logging import get_logger
from arazzo_generator.utils.utils import encode_json_pointer, to_kebab_case

logger = get_logger(__name__)


class WorkflowBuilder:
    """Builds Arazzo workflows from identified workflows."""

    def __init__(self, endpoints: dict[str, dict[str, Any]], openapi_spec: dict[str, Any] = None):
        """Initialize the workflow builder.

        Args:
            endpoints: Dictionary of endpoints from the OpenAPI parser.
            openapi_spec: The full OpenAPI specification as a dictionary.
        """
        self.endpoints = endpoints
        self.openapi_spec = openapi_spec
        self.step_id_map = {}
        self.workflow = None  # Store the original workflow

    def create_workflow(self, workflow: dict[str, Any]) -> dict[str, Any] | None:
        """Create an Arazzo workflow from an identified workflow.

        Args:
            workflow: An identified workflow from the workflow analyzer.

        Returns:
            An Arazzo workflow specification or None if invalid.
        """
        # Log the workflow for debugging
        logger.debug(f"Creating workflow from: {workflow}")

        # Get the workflow name and convert to kebab-case for workflowId
        original_name = workflow.get("name", f"workflow_{uuid.uuid4().hex[:8]}")
        workflow_id = to_kebab_case(original_name)
        workflow_type = workflow.get("type", "generic")

        # Determine workflow description
        description = workflow.get("description", "")
        if not description:
            if workflow_type == "crud":
                description = f"CRUD operations for {workflow.get('resource', 'resource')}"
            elif workflow_type == "auth":
                description = "Authentication workflow"
            elif workflow_type == "process":
                description = "Multi-step process workflow"
            else:
                description = "Generated workflow"

        # Create workflow object with basic metadata
        arazzo_workflow = {
            "workflowId": workflow_id,
            "summary": description,
            "description": description,
            # Steps will be added later
            "failureActions": [
                {"reference": "$components.failureActions.auth_failure"},
                {"reference": "$components.failureActions.permission_denied"},
                {"reference": "$components.failureActions.not_found"},
                {"reference": "$components.failureActions.server_error"},
            ],
        }

        # Dictionary to track step IDs and their corresponding operation objects
        # This will be used later for validating cross-references
        self.step_id_map = {}

        # Store the original workflow for later use
        self.workflow = workflow

        # Create steps for the workflow (but don't add them to the workflow object yet)
        steps = []
        self._create_steps(workflow, {"steps": steps})

        # If no steps were added, return None
        if not steps:
            return None

        # If only one step was added, return None as single-step workflows are not valid
        if len(steps) == 1:
            logger.warning(
                f"Workflow '{workflow_id}' contains only one step, skipping as it's not a valid workflow"
            )
            return None

        # Create a temporary workflow with steps to generate inputs and outputs
        temp_workflow = {"steps": steps}

        # Add inputs based on parameters and request bodies
        self._add_workflow_inputs(temp_workflow)

        # Add workflow outputs
        self._add_workflow_outputs(temp_workflow)

        # Now construct the final workflow with the correct order of fields
        final_workflow = {
            "workflowId": arazzo_workflow["workflowId"],
            "summary": arazzo_workflow["summary"],
            "description": arazzo_workflow["description"],
        }

        # Add inputs if present
        if "inputs" in temp_workflow:
            final_workflow["inputs"] = temp_workflow["inputs"]

        # Add steps
        final_workflow["steps"] = steps

        # Add outputs if present
        if "outputs" in temp_workflow:
            final_workflow["outputs"] = temp_workflow["outputs"]

        # Add failure actions
        final_workflow["failureActions"] = arazzo_workflow["failureActions"]

        return final_workflow

    def _create_steps(self, workflow: dict[str, Any], arazzo_workflow: dict[str, Any]) -> None:
        """Create steps for the Arazzo workflow.

        Args:
            workflow: The original workflow.
            arazzo_workflow: The Arazzo workflow being built.
        """
        for i, operation in enumerate(workflow.get("operations", [])):
            step_name = operation.get("name", f"step_{i+1}")

            for endpoint in operation.get("endpoints", []):
                if not endpoint:
                    continue

                path, method = endpoint
                if path not in self.endpoints or method not in self.endpoints[path]:
                    logger.warning(f"Endpoint {method} {path} not found in OpenAPI spec")
                    continue

                endpoint_data = self.endpoints[path][method]
                operation_id = endpoint_data.get("operation_id")

                # Get description from multiple possible sources
                description = self._get_step_description(
                    operation, endpoint_data, operation_id, method, path
                )

                # Create a more readable stepId
                step_id = to_kebab_case(step_name)

                step = {"stepId": step_id, "description": description}

                # Store the mapping between operation name and step ID
                self.step_id_map[step_name] = {
                    "step_id": step_id,
                    "operation": operation,
                }
                logger.debug(f"Mapped operation '{step_name}' to step ID '{step_id}'")

                # Add operation reference
                self._add_operation_reference(step, operation_id, path, method)

                # Add parameters
                self._add_step_parameters(step, endpoint_data, operation, i, workflow)

                # Add request body
                self._add_request_body(step, endpoint_data, operation, i, workflow)

                # Add success criteria
                step["successCriteria"] = [{"condition": "$statusCode == 200"}]

                # Add output mapping
                self._add_step_outputs(step, endpoint_data, step_name)

                # Add this step to the workflow
                arazzo_workflow["steps"].append(step)

    def _get_step_description(
        self,
        operation: dict[str, Any],
        endpoint_data: dict[str, Any],
        operation_id: str,
        method: str,
        path: str,
    ) -> str:
        """Get the description for a step from multiple possible sources.

        Args:
            operation: The operation from the workflow.
            endpoint_data: The endpoint data from the OpenAPI spec.
            operation_id: The operation ID from the OpenAPI spec.
            method: The HTTP method.
            path: The endpoint path.

        Returns:
            The step description.
        """
        # First try to get description from the operation in the LLM response
        description = operation.get("description")
        # If not available, try to get description from multiple possible fields in the OpenAPI spec
        if description is None:
            description = endpoint_data.get("summary")
        if description is None:
            description = endpoint_data.get("description")
        if description is None and operation_id:
            # Use operation_id as fallback if available
            description = f"Operation: {operation_id}"
        if description is None:
            # Final fallback uses method and path
            description = f"{method.upper()} {path}"

        return description

    def _add_operation_reference(
        self, step: dict[str, Any], operation_id: str, path: str, method: str
    ) -> None:
        """Add operation reference to a step.

        Args:
            step: The step to add the operation reference to.
            operation_id: The operation ID from the OpenAPI spec.
            path: The endpoint path.
            method: The HTTP method.
        """
        if operation_id:
            step["operationId"] = operation_id
        else:
            # Ensure path is properly encoded for JSON pointer
            encoded_path = encode_json_pointer(path)
            step["operationPath"] = f"openapi_source#/paths/{encoded_path}/{method}"

    def _resolve_reference(self, ref: str) -> dict[str, Any]:
        """Resolve a reference to its actual definition in the OpenAPI spec.

        Args:
            ref: The reference string (e.g., "#/components/parameters/PathArtistId", "#/components/schemas/User")

        Returns:
            A dictionary containing the resolved definition, or an empty dict if resolution fails.
        """
        resolved_item = {}

        try:
            # Only handle references that start with '#/components/'
            if ref.startswith("#/components/"):
                # Extract component type and key from the reference
                ref_parts = ref.split("/")
                if len(ref_parts) >= 4:
                    component_type = ref_parts[2]  # 'parameters', 'schemas', 'requestBodies', etc.
                    component_key = ref_parts[3]  # The specific component name

                    # First try to find the component in the full OpenAPI spec if available
                    if self.openapi_spec and "components" in self.openapi_spec:
                        components = self.openapi_spec.get("components", {})
                        component_dict = components.get(component_type, {})
                        if component_key in component_dict:
                            return component_dict[component_key]

                    # Fallback: Try to find the component in the endpoints data
                    for endpoint_data in self.endpoints.values():
                        # Some endpoints might have a 'components' field directly
                        if "components" in endpoint_data:
                            components = endpoint_data.get("components", {})
                            component_dict = components.get(component_type, {})
                            if component_key in component_dict:
                                return component_dict[component_key]

                logger.warning(f"Reference not found: {ref}")
            else:
                logger.warning(f"Unsupported reference format: {ref}")
        except Exception as e:
            logger.warning(f"Failed to resolve reference {ref}: {e}")

        return resolved_item

    def _add_step_parameters(
        self,
        step: dict[str, Any],
        endpoint_data: dict[str, Any],
        operation: dict[str, Any],
        i: int,
        workflow: dict[str, Any],
    ) -> None:
        """Add parameters to a step.

        Args:
            step: The step to add parameters to.
            endpoint_data: The endpoint data from the OpenAPI spec.
            operation: The operation from the workflow.
            i: The index of the operation in the workflow.
            workflow: The original workflow.
        """
        parameters = []
        param_keys = set()  # Track unique parameter name+location combinations

        for param in endpoint_data.get("parameters", []):
            param_name = None
            param_in = None

            # Check if this is a reference parameter that needs to be resolved
            if "$ref" in param:
                # Resolve the reference
                resolved_param = self._resolve_reference(param["$ref"])
                param_name = resolved_param.get("name")
                param_in = resolved_param.get("in")
            else:
                # Direct parameter definition
                param_name = param.get("name")
                param_in = param.get("in")

            if param_name and param_in:
                # Create a unique key for this parameter (name+location)
                param_key = f"{param_name}:{param_in}"

                # Skip if we've already processed this parameter
                if param_key in param_keys:
                    logger.warning(f"Skipping duplicate parameter: {param_name} in {param_in}")
                    continue

                # Add to our tracking set
                param_keys.add(param_key)

                # Check if a dependency exists for this parameter
                dependency_found = False

                # Look for dependencies if this isn't the first operation
                if i > 0 and "dependencies" in operation:
                    # Check if this parameter has a defined dependency
                    if param_name in operation.get("dependencies", {}):
                        dependency = operation["dependencies"][param_name]
                        dep_step = dependency.get("step")
                        dep_output = dependency.get("output")

                        # Find the corresponding step by name
                        for prev_i, prev_op in enumerate(workflow.get("operations", [])):
                            if prev_i < i and prev_op.get("name") == dep_step:
                                # Get the step ID from our mapping if it exists
                                prev_op_name = prev_op.get("name")
                                if prev_op_name in self.step_id_map:
                                    prev_step_id = self.step_id_map[prev_op_name]["step_id"]
                                else:
                                    # Fallback to to_kebab_case if not in mapping
                                    prev_step_id = f"{to_kebab_case(prev_op_name)}"
                                    logger.debug(
                                        f"Using generated step ID '{prev_step_id}' for operation '{prev_op_name}'"
                                    )

                                # Validate that the referenced output exists in the previous step's outputs
                                prev_outputs = prev_op.get("outputs", [])

                                # Extract base output name for validation (without array indexing or nested properties)
                                base_output = dep_output
                                if "[" in dep_output and "]" in dep_output:
                                    base_output = dep_output.split("[", 1)[0]
                                if "." in base_output:
                                    base_output = base_output.split(".", 1)[0]

                                # Check if the output exists in the previous step's outputs
                                output_exists = False
                                for output in prev_outputs:
                                    if (
                                        isinstance(output, dict)
                                        and output.get("name") == base_output
                                    ):
                                        output_exists = True
                                        break

                                # Only create the reference if the base output exists in the previous step's outputs
                                if output_exists:
                                    output_ref = f"$steps.{prev_step_id}.outputs.{dep_output}"

                                    parameters.append(
                                        {
                                            "name": param_name,
                                            "in": param_in,
                                            "value": output_ref,
                                        }
                                    )
                                    dependency_found = True
                                    logger.debug(
                                        f"Added parameter dependency: {param_name} -> {output_ref}"
                                    )
                                    break
                                else:
                                    # Log a warning if the output doesn't exist
                                    logger.warning(
                                        f"Skipping invalid dependency reference: Step '{dep_step}' does not have output '{dep_output}'"
                                    )
                                    # Fall back to using input reference
                                    # This ensures the workflow still works even if the dependency is invalid
                                    parameters.append(
                                        {
                                            "name": param_name,
                                            "in": param_in,
                                            "value": f"$inputs.{param_name}",
                                        }
                                    )
                                    dependency_found = True
                                break

                # If no dependency found, use input reference as normal
                if not dependency_found:
                    parameters.append(
                        {
                            "name": param_name,
                            "in": param_in,
                            "value": f"$inputs.{param_name}",
                        }
                    )

        if parameters:
            step["parameters"] = parameters

    def _add_request_body(
        self,
        step: dict[str, Any],
        endpoint_data: dict[str, Any],
        operation: dict[str, Any],
        i: int,
        workflow: dict[str, Any],
    ) -> None:
        """Add request body to a step.

        Args:
            step: The step to add the request body to.
            endpoint_data: The endpoint data from the OpenAPI spec.
            operation: The operation from the workflow.
            i: The index of the operation in the workflow.
            workflow: The original workflow.
        """
        request_body = endpoint_data.get("request_body")
        if request_body and "content" in request_body:
            content_types = list(request_body["content"].keys())
            if content_types:
                content_type = content_types[0]
                # Default to using inputs
                step_id = step.get("stepId", "")
                body_input_name = f"{step_id}_body"

                # Get the schema for the request body if available
                schema = None
                if "schema" in request_body["content"][content_type]:
                    schema = request_body["content"][content_type]["schema"]

                # Get the required properties from the schema if available
                required_props = []

                if "$ref" in schema:
                    resolved_schema = self._resolve_reference(schema["$ref"])
                    if resolved_schema:
                        schema = resolved_schema

                if schema and "required" in schema:
                    required_props = schema["required"]
                elif schema and "properties" in schema:
                    # If required is not specified, assume all properties are required
                    required_props = list(schema["properties"].keys())

                # Check if we have dependencies for any of the required properties
                # or any other inputs that might be part of the request body
                dependencies_found = False
                constructed_body = {}

                # First, check if any of the operation's inputs match the required properties
                # or if there are explicit dependencies for any inputs
                if "dependencies" in operation:
                    for input_name, dependency in operation.get("dependencies", {}).items():
                        # Check if this input is in the required properties or is a known input
                        if input_name in required_props or input_name in operation.get(
                            "inputs", []
                        ):
                            dep_step = dependency.get("step")
                            dep_output = dependency.get("output")

                            # Find the corresponding step by name
                            for prev_i, prev_op in enumerate(workflow.get("operations", [])):
                                if prev_i < i and prev_op.get("name") == dep_step:
                                    # Create a step reference
                                    prev_step_id = f"{to_kebab_case(prev_op.get('name'))}"

                                    # Validate that the referenced output exists in the previous step's outputs
                                    prev_outputs = prev_op.get("outputs", [])

                                    # Extract base output name for validation (without array indexing or nested properties)
                                    base_output = dep_output
                                    if "[" in dep_output and "]" in dep_output:
                                        base_output = dep_output.split("[", 1)[0]
                                    if "." in base_output:
                                        base_output = base_output.split(".", 1)[0]

                                    # Check if the output exists in the previous step's outputs
                                    output_exists = False
                                    for output in prev_outputs:
                                        if (
                                            isinstance(output, dict)
                                            and output.get("name") == base_output
                                        ):
                                            output_exists = True
                                            break

                                    # Only create the reference if the base output exists in the previous step's outputs
                                    if output_exists:
                                        output_ref = f"$steps.{prev_step_id}.outputs.{dep_output}"
                                        constructed_body[input_name] = output_ref
                                        dependencies_found = True
                                        logger.debug(
                                            f"Added request body field dependency: {input_name} -> {output_ref}"
                                        )
                                    else:
                                        # Log a warning if the output doesn't exist
                                        logger.warning(
                                            f"Skipping invalid request body field dependency: Step '{dep_step}' does not have output '{dep_output}'"
                                        )
                                    break

                # Add all required properties from the schema that don't have dependencies
                # R1
                if schema and "properties" in schema:
                    for prop_name in required_props:
                        if prop_name not in constructed_body and prop_name in operation.get(
                            "inputs", []
                        ):
                            constructed_body[prop_name] = f"$inputs.{prop_name}"
                            dependencies_found = True

                # If we found dependencies for specific fields, create a structured request body
                if dependencies_found:
                    step["requestBody"] = {
                        "contentType": content_type,
                        "payload": constructed_body,
                    }
                    logger.debug(
                        f"Created structured request body with dependencies for step {step_id}"
                    )
                else:
                    # Fall back to the default approach of using a single input for the entire body
                    payload_ref = f"$inputs.{body_input_name}"

                    # Check if a dependency exists for the entire request body
                    # Look for dependencies if this isn't the first operation
                    if i > 0 and "dependencies" in operation:
                        # Check for dependencies that might relate to the request body
                        for input_name, dependency in operation.get("dependencies", {}).items():
                            # If this is a body-related input (simple heuristic)
                            if "body" in input_name.lower() or input_name in [
                                "payload",
                                "request",
                                "data",
                            ]:
                                dep_step = dependency.get("step")
                                dep_output = dependency.get("output")

                                # Find the corresponding step by name
                                for prev_i, prev_op in enumerate(workflow.get("operations", [])):
                                    if prev_i < i and prev_op.get("name") == dep_step:
                                        # Create a step reference
                                        prev_step_id = f"{to_kebab_case(prev_op.get('name'))}"

                                        # Validate that the referenced output exists in the previous step's outputs
                                        prev_outputs = prev_op.get("outputs", [])

                                        # Extract base output name for validation (without array indexing or nested properties)
                                        base_output = dep_output
                                        if "[" in dep_output and "]" in dep_output:
                                            base_output = dep_output.split("[", 1)[0]
                                        if "." in base_output:
                                            base_output = base_output.split(".", 1)[0]

                                        # Check if the output exists in the previous step's outputs
                                        output_exists = False
                                        for output in prev_outputs:
                                            if (
                                                isinstance(output, dict)
                                                and output.get("name") == base_output
                                            ):
                                                output_exists = True
                                                break

                                        # Only create the reference if the base output exists in the previous step's outputs
                                        if output_exists:
                                            payload_ref = (
                                                f"$steps.{prev_step_id}.outputs.{dep_output}"
                                            )

                                            logger.debug(
                                                f"Added request body dependency: {input_name} -> {payload_ref}"
                                            )
                                            break
                                        else:
                                            # Log a warning if the output doesn't exist
                                            logger.warning(
                                                f"Skipping invalid request body dependency: Step '{dep_step}' does not have output '{dep_output}'"
                                            )
                                            # Keep using the default input reference
                                            logger.debug(
                                                f"Using default input reference for request body: {body_input_name}"
                                            )
                                            payload_ref = f"$inputs.{body_input_name}"
                                        break
                                if payload_ref != f"$inputs.{body_input_name}":
                                    break  # Stop looking once we've found a valid dependency

                    # Store consistent input name as a property on the step for later use
                    step["_body_input_name"] = (
                        body_input_name  # Temporary property, will be removed
                    )
                    step["requestBody"] = {
                        "contentType": content_type,
                        "payload": payload_ref,
                    }

    def _add_step_outputs(
        self, step: dict[str, Any], endpoint_data: dict[str, Any], step_name: str
    ) -> None:
        """Add outputs to a step.

        Args:
            step: The step to add outputs to.
            endpoint_data: The endpoint data from the OpenAPI spec.
            step_name: The name of the step.
        """
        logger.debug(f"Processing outputs for step: {step_name}")
        logger.debug(f"Endpoint data: {endpoint_data}")
        responses = endpoint_data.get("responses", {})
        logger.debug(f"Response codes: {list(responses.keys())}")

        # Add type checking to handle cases where response codes might be dictionaries
        success_responses = []
        for code in responses.keys():
            # Convert to string and check if it starts with '2'
            if isinstance(code, str | int) and str(code).startswith("2"):
                success_responses.append(code)

        if success_responses:
            outputs = {}
            logger.debug(f"Success response codes: {success_responses}")

            # Find the original operation in the workflow to get the LLM-defined outputs
            original_outputs = []
            for operation in self.workflow.get("operations", []):
                if operation.get("name") == step["stepId"]:
                    original_outputs = operation.get("outputs", [])
                    logger.debug(f"Found LLM outputs for step {step['stepId']}: {original_outputs}")
                    break

            # Extract response schema properties if available
            schema = self._extract_response_schema(responses, success_responses)

            # Extract response headers if available
            response_headers = self._extract_response_headers(responses, success_responses)
            logger.debug(f"Extracted response headers: {response_headers}")

            # If LLM provided outputs, use those names and map to response properties
            if original_outputs:
                # Create a mapping from LLM output names to actual response property paths
                output_mappings = self._create_output_mappings(
                    original_outputs, schema, response_headers
                )

                for output_name, property_path in output_mappings.items():
                    outputs[output_name] = property_path
            else:
                # Fallback to generating a name if no LLM outputs were provided
                # Use a cleaner naming convention for outputs
                operation_name_parts = re.sub(r"[-_]", " ", step_name).split()
                if len(operation_name_parts) > 1:
                    # Use camelCase for output names (e.g., "getUser" -> "userData")
                    output_name = f"{operation_name_parts[-1].lower()}_data"
                else:
                    output_name = f"{step_name.lower()}_data"

                outputs[output_name] = "$response.body"

            logger.debug(f"Final outputs for step {step_name}: {outputs}")
            step["outputs"] = outputs

    def _extract_response_schema(
        self, responses: dict[str, Any], success_codes: list
    ) -> dict[str, Any]:
        """Extract the response schema from the responses object.

        Args:
            responses: The responses object from the OpenAPI spec.
            success_codes: List of success response codes.

        Returns:
            The response schema as a dictionary, or an empty dict if not found.
        """
        for code in success_codes:
            response_data = responses.get(str(code), {})
            content = response_data.get("content", {})

            # Try to find JSON content type
            json_content = None
            for content_type in ["application/json", "*/*"]:
                if content_type in content:
                    json_content = content[content_type]
                    break

        if not json_content or "schema" not in json_content:
            return {}

        schema = json_content["schema"]

        # Handle schema reference
        if "$ref" in schema:
            schema = self._resolve_reference(schema["$ref"])

        # For array responses, preserve the array type information
        # but also resolve the items schema for property extraction
        if schema.get("type") == "array" and "items" in schema:
            items_schema = schema["items"]
            if "$ref" in items_schema:
                items_schema = self._resolve_reference(items_schema["$ref"])

            # Create a new schema that preserves array type but includes item properties
            array_schema = {
                "type": "array",
                "items": items_schema,
                "is_array": True,  # Custom flag to indicate array type
            }

            # If items have properties, add them to the array schema for property extraction
            if "properties" in items_schema:
                array_schema["item_properties"] = items_schema.get("properties", {})
                return array_schema
            else:
                # If items don't have properties, return the items schema directly
                # but preserve the array type information
                return array_schema

        # Return the schema if it has properties
        if "properties" in schema:
            return schema

    def _extract_response_headers(
        self, responses: dict[str, Any], success_codes: list
    ) -> dict[str, Any]:
        """Extract the response headers from the responses object.

        Args:
            responses: The responses object from the OpenAPI spec.
            success_codes: List of success response codes.

        Returns:
            The response headers as a dictionary, or an empty dict if not found.
        """
        for code in success_codes:
            response_data = responses.get(str(code), {})
            headers = response_data.get("headers", {})

            # Return the headers if they exist
            if headers:
                return headers

        # No headers found
        return {}

    def _create_output_mappings(
        self, output_names: list, schema: dict[str, Any], headers: dict[str, Any]
    ) -> dict[str, str]:
        """Create mappings from LLM output names to response property paths.

        Args:
            output_names: List of output names provided by the LLM. Can be strings or dicts with name and source.
            schema: The response schema.
            headers: The response headers.

        Returns:
            A dictionary mapping output names to property paths.
        """
        # Handle case when schema is None
        if schema is None:
            schema = {}
            logger.debug("Response schema is None, using empty schema")

        mappings = {}

        # Check if the response is an array
        is_array_response = schema.get("type") == "array" and schema.get("is_array", False)

        # Get the appropriate properties based on schema type
        if is_array_response and "item_properties" in schema:
            # For array responses, use the item properties
            properties = schema.get("item_properties", {})
            logger.debug(f"Response is an array. Using item properties: {properties}")
        else:
            # For object responses, use the regular properties
            properties = schema.get("properties", {})

        # Create a flattened view of the schema with paths
        flat_schema = self._flatten_schema(properties)

        # Add headers to the flattened schema with their full paths
        header_schema = {}
        for header_name in headers:
            header_schema[header_name] = f"$response.headers.{header_name}"

        for output_item in output_names:
            # Handle both string outputs and detailed output format
            if isinstance(output_item, dict) and "name" in output_item and "source" in output_item:
                output_name = output_item["name"]
                output_source = output_item["source"].lower()

                logger.debug(f"Processing detailed output: {output_name} from {output_source}")

                if output_source == "header":
                    # For header outputs, try to find a matching header
                    if output_name in header_schema:
                        mappings[output_name] = header_schema[output_name]
                    else:
                        # If no exact match, try to find a case-insensitive match
                        for header_name, path in header_schema.items():
                            if header_name.lower() == output_name.lower():
                                mappings[output_name] = path
                                break
                        else:
                            # If still no match, use a generic header reference
                            mappings[output_name] = f"$response.headers.{output_name}"
                else:
                    # For body outputs, use the regular property matching
                    property_path = self._find_best_property_match(output_name, flat_schema)

                    # If this is an array response and the property path doesn't already include an array index
                    if is_array_response and not any(
                        segment.isdigit() for segment in property_path.split("/")
                    ):
                        # For array responses, we need to add the array index to access the first item
                        # If the property path is just the property name (e.g., #/id), add /0 before it
                        if property_path.startswith("#/"):
                            # Insert the array index after the # but before the property name
                            property_path = f"#/0{property_path[1:]}"
                        else:
                            # For other paths, just prepend the array index
                            property_path = f"#/0{property_path}"

                    mappings[output_name] = f"$response.body{property_path}"
            else:
                # Handle simple string output (assumed to be from body)
                output_name = output_item
                property_path = self._find_best_property_match(output_name, flat_schema)

                # If this is an array response and the property path doesn't already include an array index
                if is_array_response and not any(
                    segment.isdigit() for segment in property_path.split("/")
                ):
                    # For array responses, we need to add the array index to access the first item
                    # If the property path is just the property name (e.g., #/id), add /0 before it
                    if property_path.startswith("#/"):
                        # Insert the array index after the # but before the property name
                        property_path = f"#/0{property_path[1:]}"
                    else:
                        # For other paths, just prepend the array index
                        property_path = f"#/0{property_path}"

                mappings[output_name] = f"$response.body{property_path}"

        return mappings

    def _flatten_schema(self, properties: dict[str, Any], prefix: str = "") -> dict[str, str]:
        """Flatten a nested schema into a dictionary of property paths.

        Args:
            properties: The properties object from the schema.
            prefix: The prefix for nested properties.

        Returns:
            A dictionary mapping property names to their paths.
        """
        result = {}

        for prop_name, prop_schema in properties.items():
            # Add the current property
            if not prefix:
                # Root level property
                path = f"#/{prop_name}"
            else:
                # Nested property - use forward slash for path segments
                path = f"{prefix}/{prop_name}"

            result[prop_name] = path

            # Handle nested objects
            if prop_schema.get("type") == "object" and "properties" in prop_schema:
                nested = self._flatten_schema(prop_schema["properties"], path)
                result.update(nested)

            # Handle arrays with object items
            if prop_schema.get("type") == "array" and "items" in prop_schema:
                items = prop_schema["items"]
                if items.get("type") == "object" and "properties" in items:
                    # For array items, append /0 to indicate first array element using JSON Pointer syntax
                    array_path = f"{path}/0"
                    nested = self._flatten_schema(items["properties"], array_path)
                    result.update(nested)

        return result

    def _find_best_property_match(self, output_name: str, flat_schema: dict[str, str]) -> str:
        """Find the best matching property in the schema for an output name.

        Args:
            output_name: The output name provided by the LLM.
            flat_schema: The flattened schema with property paths.

        Returns:
            The path to the matching property, or the original output name if no match is found.
        """

        # If exact match exists, use it
        if output_name in flat_schema:
            return flat_schema[output_name]

        # Normalize and try again
        normalized_output = output_name.lower().replace("_", "").replace("-", "")
        for prop_name, path in flat_schema.items():
            normalized_prop = prop_name.lower().replace("_", "").replace("-", "")
            if normalized_output == normalized_prop:
                return path

        # Special case for ID fields
        if output_name.endswith("_id") and "id" in flat_schema:
            return flat_schema["id"]

        # Fuzzy match using Levenshtein distance
        best_match = None
        best_score = 0

        for prop_name, path in flat_schema.items():
            # Calculate normalized Levenshtein ratio (0-1 where 1 is exact match)
            distance_value = distance(output_name.lower(), prop_name.lower())
            max_len = max(len(output_name), len(prop_name))
            score = 1 - (distance_value / max_len) if max_len > 0 else 0

            if score > best_score and score > 0.7:  # Higher threshold for more confidence
                best_score = score
                best_match = path

        if best_match:
            return best_match

        # Default fallback
        return f"#/{output_name}"

    def _calculate_levenshtein_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity based on Levenshtein distance.

        Args:
            str1: First string.
            str2: Second string.

        Returns:
            A similarity score between 0 and 1.
        """
        # This method is no longer used - we're using the Levenshtein library directly
        # Keeping as a placeholder in case we need to revert
        return 0.0

    def _add_workflow_inputs(self, arazzo_workflow: dict[str, Any]) -> None:
        """Add inputs to the workflow based on parameters and request bodies.

        Args:
            arazzo_workflow: The Arazzo workflow to add inputs to.
        """
        input_properties = {}
        for step in arazzo_workflow["steps"]:
            # Add parameter inputs
            for param in step.get("parameters", []):
                param_name = param.get("name")
                if param_name:
                    input_properties[param_name] = {"type": "string"}

            # Add request body inputs
            if "requestBody" in step:
                # Use the same input name that was stored when creating the request body
                if "_body_input_name" in step:
                    body_name = step["_body_input_name"]
                    # Remove the temporary property
                    del step["_body_input_name"]
                else:
                    # Fallback for backward compatibility
                    # Extract from the request body content reference if available
                    if "requestBody" in step and "payload" in step["requestBody"]:
                        payload_ref = step["requestBody"]["payload"]
                        # Check if payload_ref is a string (simple reference) or a dict (structured body)
                        if isinstance(payload_ref, str) and payload_ref.startswith("$inputs."):
                            body_name = payload_ref[8:]  # Remove "$inputs." prefix
                            input_properties[body_name] = {"type": "object"}
                        elif isinstance(payload_ref, dict):
                            # For structured request bodies, we need to extract any input references
                            # and add them to the workflow inputs
                            for field_value in payload_ref.values():
                                if isinstance(field_value, str) and field_value.startswith(
                                    "$inputs."
                                ):
                                    input_name = field_value[8:]  # Remove "$inputs." prefix
                                    input_properties[input_name] = {"type": "string"}
                            # Skip creating a single input for the entire body
                            continue
                        else:
                            # Last resort fallback
                            step_id = step.get("stepId", "")
                            body_name = f"{step_id}_body"

                input_properties[body_name] = {"type": "object"}

        if input_properties:
            arazzo_workflow["inputs"] = {
                "type": "object",
                "properties": input_properties,
            }

    def _add_workflow_outputs(self, arazzo_workflow: dict[str, Any]) -> None:
        """Add outputs to the workflow based on step outputs.

        Args:
            arazzo_workflow: The Arazzo workflow to add outputs to.
        """
        outputs = {}

        # Collect outputs from all steps
        for step in arazzo_workflow["steps"]:
            step_outputs = step.get("outputs", {})
            for output_name in step_outputs:
                # Format the reference in a way that ensures it stays on one line
                reference = f"$steps.{step['stepId']}.outputs.{output_name}"
                outputs[output_name] = reference

        # Add outputs to the workflow if there are any
        if outputs:
            arazzo_workflow["outputs"] = outputs
