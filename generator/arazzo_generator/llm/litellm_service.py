"""LiteLLM-based service for enhancing workflow analysis and generation."""

import datetime
import json
import os
import pathlib
import re
from typing import Any

import litellm
from litellm import completion

from ..utils.config import get_config
from ..utils.logging import get_logger, log_llm_prompt, log_llm_response, setup_log_directory


# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date | datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)


logger = get_logger(__name__)


class LiteLLMService:
    """LiteLLM-based service for enhancing workflow analysis and generation.

    This class provides methods to interact with any LLM provider supported by LiteLLM
    for analyzing OpenAPI endpoints and generating enhanced workflows.
    """

    def __init__(
        self,
        # Default to None to indicate we'll use config values
        llm_model: str | None = None,
        api_key: str | None = None,
        llm_provider: str | None = None,
        temperature: float | None = None,
    ):
        """Initialize the LiteLLM service.

        Args:
            model: Model name to use (e.g., "gemini/gemini-2.5-flash-preview-05-20", "gpt-4o", "claude-3-sonnet-20240229").
                   If not provided, will use the model from config.toml.
            provider: LLM provider to use ("gemini", "anthropic", "openai").
                     If not provided, will use the provider from config.toml.
            temperature: Temperature for response generation (0.0-1.0).
            api_key: API key for the model provider. If not provided, LiteLLM will check
                    environment variables automatically.
        """
        # Get default values from config
        config = get_config()

        if llm_model and not llm_provider:
            raise ValueError("LLM model provided through CLI arg without LLM provider")

        if llm_provider and not llm_model:
            raise ValueError("LLM provider provided through CLI arg without LLM model")

        # Set provider (CLI arg > config)
        self.llm_provider = llm_provider or config.llm.llm_provider

        # Set model (CLI arg > config)
        self.llm_model = llm_model or config.llm.llm_model

        self.temperature = temperature or 0.1

        # Initialize fallback_models to prevent attribute errors
        self.fallback_models = []

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv(f"{self.llm_provider.upper()}_API_KEY")

        # Configure LiteLLM
        litellm.drop_params = True
        litellm.set_verbose = False

        if self.api_key:
            logger.info(f"Using API key for {self.llm_provider}")
        else:
            # Log warning if no API key is found
            logger.warning(
                f"No API key provided for {self.llm_provider} LLM service. "
                f"Please set the {self.llm_provider.upper()}_API_KEY environment variable."
            )

        logger.info(
            f"Initialized LiteLLM service with model: {self.llm_model} (provider: {self.llm_provider})"
        )

    def is_available(self) -> bool:
        """Check if the LLM service is available.

        Returns:
            True if the service can make requests, False otherwise.
        """
        try:
            # Try a simple completion to test availability
            response = litellm.completion(
                model=self.llm_model,
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0,
                max_tokens=1,  # Use minimal tokens for availability check
                api_key=self.api_key,
            )
            return response is not None
        except Exception as e:
            logger.warning(f"LLM service not available: {str(e)}")
            return False

    def _make_request(self, prompt: str, log_prefix: str = "request") -> str:
        """Make a request to the LLM with fallback support.

        Args:
            prompt: The prompt to send to the LLM.
            log_prefix: Prefix for log files.

        Returns:
            The LLM response text.
        """
        messages = [{"role": "user", "content": prompt}]

        # Try primary model first
        models_to_try = [self.llm_model] + self.fallback_models

        for model in models_to_try:
            try:
                logger.info(f"Making request to {model}")

                response = completion(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    api_key=self.api_key,
                )

                response_text = response.choices[0].message.content

                # Handle None or empty response content
                if response_text is None:
                    logger.warning(
                        f"Model {model} returned None content, attempting retry with lower max_tokens"
                    )

                    # Retry with reduced max_tokens to avoid truncation
                    try:
                        retry_response = completion(
                            model=model,
                            messages=messages,
                            temperature=self.temperature,
                            max_tokens=10000,
                            api_key=self.api_key,
                        )

                        retry_text = retry_response.choices[0].message.content
                        if retry_text is not None:
                            logger.info("Retry successful with reduced max_tokens")
                            response_text = retry_text
                        else:
                            logger.warning("Retry also returned None content")
                            response_text = ""

                        # Log retry usage statistics if available
                        if hasattr(retry_response, "usage") and retry_response.usage:
                            logger.info(
                                f"Retry token usage - Prompt: {retry_response.usage.prompt_tokens}, "
                                f"Completion: {retry_response.usage.completion_tokens}, "
                                f"Total: {retry_response.usage.total_tokens}"
                            )
                    except Exception as retry_e:
                        logger.warning(f"Retry failed: {str(retry_e)}")
                        response_text = ""

                # Log usage statistics if available
                if hasattr(response, "usage") and response.usage:
                    logger.info(
                        f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                        f"Completion: {response.usage.completion_tokens}, "
                        f"Total: {response.usage.total_tokens}"
                    )

                return response_text

            except Exception as e:
                logger.warning(f"Request failed for model {model}: {str(e)}")
                if model == models_to_try[-1]:  # Last model in list
                    raise Exception(f"All models failed. Last error: {str(e)}") from e
                continue

    def analyze_endpoints(
        self,
        endpoints: dict[str, dict[str, Any]],
        schemas: dict[str, Any],
        parameters: dict[str, Any],
        responses: dict[str, Any],
        request_bodies: dict[str, Any],
        spec: dict[str, Any] = None,
        user_workflow_descriptions: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Analyze endpoints to identify workflows.

        Args:
            endpoints: Dictionary of endpoints from the OpenAPI spec.
            schemas: Dictionary of schemas from the OpenAPI spec.
            parameters: Dictionary of parameters from the OpenAPI spec.
            responses: Dictionary of responses from the OpenAPI spec.
            request_bodies: Dictionary of request bodies from the OpenAPI spec.
            spec: The full OpenAPI spec to extract metadata from.
            user_workflow_descriptions: Optional list of user-provided workflow descriptions.

        Returns:
            List of identified workflows.
        """
        logger.debug("analyze_endpoints called")

        if not self.is_available():
            logger.warning("LLM service not available. Skipping LLM-based analysis.")
            return []

        logger.info("Starting LLM-based endpoint analysis for workflow identification")

        try:
            # Format the endpoints and schemas into a readable format for the LLM
            formatted_endpoints = self._format_endpoints_for_llm(endpoints)

            # Extract metadata if spec is available
            metadata = None
            if spec:
                metadata = self._extract_api_metadata(spec)

            # Build prompt for the LLM with metadata if available
            prompt = self._build_endpoint_analysis_prompt(
                formatted_endpoints=formatted_endpoints,
                schemas=schemas,
                parameters=parameters,
                responses=responses,
                request_bodies=request_bodies,
                metadata=metadata,
                user_workflow_descriptions=user_workflow_descriptions,
            )

            # Set up logging directory for this analysis
            logger.debug("Setting up log directory")
            log_dir, timestamp = setup_log_directory()
            logger.debug(f"Log directory: {log_dir}, timestamp: {timestamp}")

            # Log the prompt
            logger.debug("Logging LLM prompt")
            log_llm_prompt(prompt, log_dir, "workflow_analysis", timestamp)

            # Send request to LLM
            logger.debug("Sending request to LLM")
            response = self._make_request(prompt, "workflow_analysis")

            # Log the response
            logger.debug("Logging LLM response")
            log_llm_response(response, log_dir, "workflow_analysis")

            # Parse the response
            workflows = self._parse_workflow_response(response)

            logger.info(f"LLM identified {len(workflows)} workflows")
            return workflows

        except Exception as e:
            logger.error(f"Error in LLM workflow analysis: {str(e)}")
            return []

    def _format_endpoints_for_llm(self, endpoints: dict[str, dict[str, Any]]) -> str:
        """Format endpoints in a readable format for the LLM.

        Args:
            endpoints: Dictionary of endpoints from the OpenAPI spec.

        Returns:
            String representation of endpoints with only JSON content types to reduce prompt size.
        """
        formatted_endpoints = []

        for path, methods in endpoints.items():
            for method, operation in methods.items():
                # Preserve request and response schema references instead of expanding them

                # Process parameters (preserve refs)
                parameters = []
                for param in operation.get("parameters", []):
                    if "$ref" in param:
                        # Keep the reference intact
                        parameters.append({"$ref": param["$ref"]})
                    else:
                        # For non-ref parameters, preserve schema references if they exist
                        param_copy = param.copy()
                        if "schema" in param_copy and "$ref" in param_copy["schema"]:
                            # Keep only the schema reference
                            param_copy["schema"] = {"$ref": param_copy["schema"]["$ref"]}
                        parameters.append(param_copy)

                # Process request body (preserve refs)
                request_body = {}
                orig_request_body = operation.get("request_body", {})

                if "$ref" in orig_request_body:
                    # Direct reference - keep it intact
                    request_body = {"$ref": orig_request_body["$ref"]}
                elif "content" in orig_request_body:
                    # Copy the request body structure
                    request_body = {k: v for k, v in orig_request_body.items() if k != "content"}
                    content = {}

                    # Extract just the JSON content type if available, otherwise use first available
                    json_type = "application/json"
                    content_types = list(orig_request_body["content"].keys())
                    content_type = (
                        json_type
                        if json_type in content_types
                        else (content_types[0] if content_types else None)
                    )

                    if content_type:
                        content_obj = orig_request_body["content"][content_type]
                        # Check if schema has a reference and preserve it
                        if "schema" in content_obj and "$ref" in content_obj["schema"]:
                            content[content_type] = {
                                "schema": {"$ref": content_obj["schema"]["$ref"]}
                            }
                        else:
                            content[content_type] = content_obj

                    request_body["content"] = content

                # Process responses (preserve refs)
                responses = {}
                for status, response in operation.get("responses", {}).items():
                    if "$ref" in response:
                        # Direct reference - keep it intact
                        responses[status] = {"$ref": response["$ref"]}
                    elif "content" in response:
                        # Copy the response structure
                        responses[status] = {k: v for k, v in response.items() if k != "content"}
                        content = {}

                        # Extract just one content type (prefer JSON)
                        content_types = list(response["content"].keys())
                        content_type = (
                            "application/json"
                            if "application/json" in content_types
                            else (content_types[0] if content_types else None)
                        )

                        if content_type:
                            content_obj = response["content"][content_type]
                            # Check if schema has a reference and preserve it
                            if "schema" in content_obj and "$ref" in content_obj["schema"]:
                                content[content_type] = {
                                    "schema": {"$ref": content_obj["schema"]["$ref"]}
                                }
                            else:
                                content[content_type] = content_obj

                        responses[status]["content"] = content
                    else:
                        responses[status] = response

                endpoint_info = {
                    "path": path,
                    "method": method,
                    "operation_id": operation.get("operation_id", ""),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "parameters": parameters,
                    "request_body": request_body,
                    "responses": responses,
                    "tags": operation.get("tags", []),
                }
                formatted_endpoints.append(endpoint_info)

        try:
            # Use the custom encoder to handle datetime objects
            return json.dumps(formatted_endpoints, cls=DateTimeEncoder)
        except TypeError as e:
            logger.warning(f"Error serializing endpoints: {e}")
            # Fallback to a simpler representation
            simplified_endpoints = []
            for endpoint in formatted_endpoints:
                simplified_endpoints.append(
                    {
                        "path": endpoint["path"],
                        "method": endpoint["method"],
                        "operation_id": endpoint["operation_id"],
                        "summary": endpoint["summary"],
                        "tags": endpoint["tags"],
                    }
                )
            return json.dumps(simplified_endpoints, indent=2)

    def _extract_api_metadata(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Extract key metadata from the OpenAPI specification.

        Args:
            spec: The complete OpenAPI specification.

        Returns:
            Dictionary containing key metadata elements.
        """
        # Extract only important metadata fields that provide context
        metadata = {
            "title": spec.get("info", {}).get("title", ""),
            "description": spec.get("info", {}).get("description", ""),
            "version": spec.get("info", {}).get("version", ""),
            "terms_of_service": spec.get("info", {}).get("termsOfService", ""),
            "contact": spec.get("info", {}).get("contact", {}),
            "license": spec.get("info", {}).get("license", {}),
            "servers": spec.get("servers", []),
            "security": spec.get("security", []),
            "tags": spec.get("tags", []),
            "external_docs": spec.get("externalDocs", {}),
        }

        return metadata

    def _format_user_workflow_section(self, user_workflow_descriptions: list[str] | None) -> str:
        """Formats the user-requested workflow descriptions into a string section for the prompt.

        Args:
            user_workflow_descriptions: Optional list of user-provided workflow descriptions.

        Returns:
            A formatted string section or an empty string if no descriptions are provided.
        """
        if not user_workflow_descriptions:
            return ""

        # Format the list of descriptions
        formatted_descriptions_list = "\n".join(f"- {desc}" for desc in user_workflow_descriptions)

        # Read the template file
        prompt_file = (
            pathlib.Path(__file__).parent / "prompts" / "user_workflow_instructions.prompt"
        )
        try:
            with open(prompt_file) as f:
                prompt_template = f.read()

            # Replace the placeholder with the formatted list
            return prompt_template.replace("{formatted_descriptions}", formatted_descriptions_list)
        except FileNotFoundError:
            logger.error(f"User workflow instructions prompt file not found: {prompt_file}")
            # Fallback or raise an error if the template is crucial
            return ""  # Return empty string on error for now

    def _build_endpoint_analysis_prompt(
        self,
        formatted_endpoints: str,
        schemas: dict[str, Any],
        parameters: dict[str, Any],
        responses: dict[str, Any],
        request_bodies: dict[str, Any],
        metadata: dict[str, Any] = None,
        user_workflow_descriptions: list[str] | None = None,
    ) -> str:
        """Build a prompt for endpoint analysis.

        Args:
            formatted_endpoints: Formatted endpoints as string.
            schemas: Dictionary of schemas from the OpenAPI spec.
            metadata: Optional API metadata extracted from the spec.
            user_workflow_descriptions: Optional list of user-provided workflow descriptions.

        Returns:
            Prompt for the LLM.
        """
        # Extract schema names for reference
        schema_names = list(schemas.keys())

        # Format components for inclusion in the prompt
        formatted_schemas = json.dumps(schemas, cls=DateTimeEncoder)
        formatted_parameters = json.dumps(parameters, cls=DateTimeEncoder)
        formatted_responses = json.dumps(responses, cls=DateTimeEncoder)
        formatted_request_bodies = json.dumps(request_bodies, cls=DateTimeEncoder)

        # Create metadata section only if metadata is available
        metadata_section = ""
        if metadata:
            formatted_metadata = json.dumps(metadata, cls=DateTimeEncoder)
            metadata_section = f"USE API DATA TO THINK AND INFER MORE CONTEXT ABOUT THE COMPANY AND HOW USERS USE THEIR SERVICES WHEN CREATING WORKFLOWS \nAPI METADATA:\n{formatted_metadata}\n\n"

        # Get the formatted user workflow section using the helper method
        logger.info(f"Workflow descriptions received: {user_workflow_descriptions}")
        workflow_section = self._format_user_workflow_section(user_workflow_descriptions)

        # Get the prompt template file path
        prompt_file = pathlib.Path(__file__).parent / "prompts" / "endpoint_analysis.prompt"

        try:
            # Read the prompt template
            with open(prompt_file) as f:
                prompt_template = f.read()

            # Use safe string replace instead of format to avoid issues with JSON examples
            # that contain curly braces which can be misinterpreted as format placeholders
            prompt = prompt_template.replace("{endpoints}", formatted_endpoints)
            prompt = prompt.replace("{schema_types}", formatted_schemas)
            prompt = prompt.replace("{parameters}", formatted_parameters)
            prompt = prompt.replace("{responses}", formatted_responses)
            prompt = prompt.replace("{requestBodies}", formatted_request_bodies)
            prompt = prompt.replace("{metadata_section}", metadata_section)
            # Replace the user workflow placeholder (assuming it's called {user_workflows})
            # If no descriptions, replaces with an empty string, effectively removing the section
            prompt = prompt.replace("{user_workflows}", workflow_section)

            return prompt

        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_file}. Using fallback prompt.")
            # Fallback to a basic prompt if file not found
            metadata_section = ""
            if metadata:
                formatted_metadata = json.dumps(metadata, indent=2, cls=DateTimeEncoder)
                metadata_section = f"""API METADATA:
{formatted_metadata}

"""

            return f"""Analyze the OpenAPI endpoints and identify workflows.

{metadata_section}Endpoints: {formatted_endpoints}
Schema types: {", ".join(schema_names)}
Schema definitions: {formatted_schemas}
Return a JSON array of workflow definitions with: name, description, type, operations (with name and endpoints), and rank (1-10).
"""

    def _parse_workflow_response(self, response: str) -> list[dict[str, Any]]:
        """Parse the LLM response for workflow analysis.

        Args:
            response: Response from the LLM.

        Returns:
            List of identified workflows.
        """
        try:
            # Check for empty or None response
            if not response or response.strip() == "":
                logger.warning("Received empty response from LLM")
                return []

            # Log the first part of the response for debugging
            logger.debug(f"Raw LLM response (first 200 chars): {response[:200]}")

            # Try to extract JSON from code blocks first (most common format)
            import re

            json_match = re.search(r"```(?:json)?\n(.*?)\n```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                logger.debug("Found JSON in code block")
            else:
                # Look for JSON array pattern if no code block
                json_match = re.search(r"\[\s*\{.*\}\s*\]", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0).strip()
                    logger.debug("Found JSON array with brackets")
                else:
                    # Fallback to using the entire response
                    json_str = response.strip()
                    logger.debug("Using entire response")

            # Save extracted text for debugging
            with open("extracted_json.txt", "w") as f:
                f.write(json_str)

            # Basic cleanup of common JSON formatting issues
            json_str = json_str.replace("\\'", "'")  # Fix escaped single quotes
            json_str = json_str.replace('\\"', '"')  # Fix escaped double quotes
            json_str = re.sub(r",\s*\]", "]", json_str)  # Remove trailing commas in arrays
            json_str = re.sub(r",\s*}", "}", json_str)  # Remove trailing commas in objects

            # First attempt: Try to parse the entire JSON array
            try:
                workflows = json.loads(json_str)
                logger.debug(f"Successfully parsed complete JSON, found {len(workflows)} workflows")

                # Process workflows to ensure they have the required fields
                processed_workflows = self._process_workflows(workflows)
                return processed_workflows

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse full JSON: {e}")

                # Second attempt: Try to recover by parsing individual workflows
                logger.info("Attempting to recover by parsing individual complete workflows...")
                workflows = self._recover_workflows_from_malformed_json(json_str)

                if workflows:
                    logger.info(
                        f"Successfully recovered {len(workflows)} workflows from malformed JSON"
                    )
                    # Process workflows to ensure they have the required fields
                    processed_workflows = self._process_workflows(workflows)
                    return processed_workflows
                else:
                    logger.error("Could not recover any workflows from JSON")
                    return []

        except Exception:
            logger.error("Error parsing LLM workflow response: {e}")
            return []

    def _process_workflows(self, workflows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure workflows have all required fields.

        Args:
            workflows: List of workflow dictionaries.

        Returns:
            Processed workflows with all required fields.
        """
        for workflow in workflows:
            # Add workflowId if missing
            if "name" in workflow and "workflowId" not in workflow:
                workflow["workflowId"] = workflow["name"]

            # Ensure rank field exists
            if "rank" not in workflow:
                workflow["rank"] = 5  # Default mid-level rank

            # Ensure operations have descriptions
            if "operations" in workflow:
                for operation in workflow["operations"]:
                    if "description" not in operation:
                        operation_name = operation.get("name", "")
                        operation["description"] = f"Performs the {operation_name} operation"

                    # Ensure dependencies exists
                    if "dependencies" not in operation:
                        operation["dependencies"] = {}

        return workflows

    def _recover_workflows_from_malformed_json(self, json_str: str) -> list[dict[str, Any]]:
        """Attempt to recover valid workflows from malformed JSON.

        Args:
            json_str: The potentially malformed JSON string.

        Returns:
            List of successfully recovered workflow dictionaries.
        """
        # Ensure we're starting with an array
        if not json_str.strip().startswith("["):
            json_str = "[" + json_str.strip()
        if not json_str.strip().endswith("]"):
            json_str = json_str.strip() + "]"

        # Try to extract complete workflow objects using regex
        workflows = []
        workflow_pattern = r'\{\s*"name"\s*:\s*"[^"]+?"(?:.*?)(?:"rank"\s*:\s*\d+\s*\})'
        workflow_matches = re.findall(workflow_pattern, json_str, re.DOTALL)

        for workflow_str in workflow_matches:
            try:
                # Add surrounding brackets to make it a valid JSON array with one item
                test_json = "[" + workflow_str + "]"
                workflow = json.loads(test_json)[0]  # Extract the first item

                # Verify it has the minimum required fields
                if all(
                    key in workflow for key in ["name", "description", "type", "operations", "rank"]
                ):
                    workflows.append(workflow)
            except json.JSONDecodeError:
                continue  # Skip any workflow that can't be parsed

        # If we couldn't recover any complete workflows, try a fallback approach
        if not workflows:
            # Try to find partial workflows and fix them
            partial_pattern = r'\{\s*"name"\s*:\s*"[^"]+?"(?:.*?)(?:"operations"\s*:\s*\[[^\]]*\])'
            partial_matches = re.findall(partial_pattern, json_str, re.DOTALL)

            for partial_str in partial_matches:
                try:
                    # Add missing fields to make it a valid workflow
                    fixed_workflow = partial_str + ', "rank": 5}'
                    test_json = "[" + fixed_workflow + "]"
                    workflow = json.loads(test_json)[0]  # Extract the first item

                    # Verify it has the minimum required fields
                    if all(key in workflow for key in ["name", "description", "operations"]):
                        # Add missing fields
                        if "type" not in workflow:
                            workflow["type"] = "process"
                        if "rank" not in workflow:
                            workflow["rank"] = 5

                        workflows.append(workflow)
                except json.JSONDecodeError:
                    continue  # Skip any workflow that can't be parsed

        return workflows
