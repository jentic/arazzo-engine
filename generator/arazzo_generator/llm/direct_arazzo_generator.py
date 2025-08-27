"""Direct Arazzo specification generation using LLM.

This module allows direct generation of Arazzo specifications from OpenAPI specs
using LLMs, bypassing the traditional generator workflow.
"""

import json
import pathlib
from typing import Any

from ..generator.output_mapping_validator import OutputMappingValidator
from ..generator.reference_validator import ReferenceValidator
from ..llm.litellm_service import DateTimeEncoder, LiteLLMService
from ..utils.logging import get_logger, log_llm_prompt, log_llm_response, setup_log_directory
from ..utils.serializer import ArazzoSerializer

logger = get_logger(__name__)


class DirectArazzoGenerator:
    """Directly generates Arazzo specifications using LLM.

    This class bypasses the traditional workflow identification and generation steps,
    instead asking the LLM to generate a complete Arazzo specification in one step.
    """

    def __init__(
        self,
        openapi_spec_url: str,
        endpoints: dict[str, dict[str, Any]],
        schemas: dict[str, Any],
        parameters: dict[str, Any],
        responses: dict[str, Any],
        request_bodies: dict[str, Any],
        openapi_spec: dict[str, Any] = None,
        api_key: str | None = None,
        llm_model: str | None = None,
        llm_provider: str | None = None,
        workflow_descriptions: list[str] | None = None,
    ):
        """Initialize the direct Arazzo generator.

        Args:
            openapi_spec_url: URL to the original OpenAPI specification.
            endpoints: Dictionary of endpoints from the OpenAPI parser.
            schemas: Dictionary of schemas from the OpenAPI spec.
            parameters: Dictionary of parameters from the OpenAPI spec.
            responses: Dictionary of responses from the OpenAPI spec.
            request_bodies: Dictionary of request bodies from the OpenAPI spec.
            openapi_spec: The full OpenAPI specification as a dictionary.
            api_key: API key for the LLM service (overrides config if provided).
            llm_model: LLM model to use (overrides config if provided).
            llm_provider: LLM provider to use (overrides config if provided).
            workflow_descriptions: Optional list of user-requested workflow descriptions.
        """
        self.openapi_spec_url = openapi_spec_url
        self.endpoints = endpoints
        self.schemas = schemas
        self.parameters = parameters
        self.responses = responses
        self.request_bodies = request_bodies
        self.openapi_spec = openapi_spec
        self.workflow_descriptions = workflow_descriptions

        # Initialize LLM service with provided config or use defaults from config
        llm_kwargs = {}
        if api_key is not None:
            llm_kwargs["api_key"] = api_key
        if llm_model is not None:
            llm_kwargs["llm_model"] = llm_model
        if llm_provider is not None:
            llm_kwargs["llm_provider"] = llm_provider

        self.llm_service = LiteLLMService(**llm_kwargs)
        self.arazzo_spec = {}

        # Set up logging directory
        self.log_dir, _ = setup_log_directory()

    def is_available(self) -> bool:
        """Check if the LLM service is available.

        Returns:
            True if the LLM service is available, False otherwise.
        """
        return self.llm_service.is_available()

    def generate(self) -> dict[str, Any]:
        """Generate an Arazzo specification directly using the LLM.

        Returns:
            The generated Arazzo specification as a dictionary.
            Returns None if generation fails.
        """
        if not self.is_available():
            logger.warning("LLM service not available. Cannot generate Arazzo specification.")
            return None

        try:
            logger.info("Generating Arazzo specification directly using LLM")

            # Build prompt for direct Arazzo generation
            prompt = self._build_direct_generation_prompt()

            # Log the prompt
            log_llm_prompt(prompt, self.log_dir, "direct_generation")

            # Send the prompt to the LLM
            response = self.llm_service._make_request(prompt, "direct_generation")

            # Log the response
            log_llm_response(response, self.log_dir, "direct_generation")

            # Extract and parse Arazzo specification from LLM response
            arazzo_json = self._extract_arazzo_from_response(response)

            if not arazzo_json:
                logger.error("Failed to extract valid Arazzo specification from LLM response")
                return None

            # Validate and fix step references in each workflow
            if "workflows" in arazzo_json and arazzo_json["workflows"]:
                logger.info("Validating workflows in generated Arazzo specification")
                for i, workflow in enumerate(arazzo_json["workflows"]):
                    workflow_id = workflow.get("workflowId", f"workflow_{i}")

                    # Validate step references
                    logger.debug(f"Validating step references for workflow: {workflow_id}")
                    arazzo_json["workflows"][i] = ReferenceValidator.validate_step_references(
                        workflow
                    )

                    # Validate output mappings
                    logger.debug(f"Validating output mappings for workflow: {workflow_id}")
                    arazzo_json["workflows"][i] = OutputMappingValidator.validate_output_mappings(
                        workflow, self.openapi_spec, self.endpoints
                    )

            self.arazzo_spec = arazzo_json
            return self.arazzo_spec

        except Exception as e:
            logger.error(f"Error generating Arazzo specification: {e}")
            return None

    def _build_direct_generation_prompt(self) -> str:
        """Build a prompt for direct Arazzo specification generation.

        Returns:
            Prompt for the LLM.
        """
        # Format endpoints for the LLM
        formatted_endpoints = self.llm_service._format_endpoints_for_llm(self.endpoints)

        # Extract API metadata if available
        metadata = {}
        if self.openapi_spec:
            metadata = self.llm_service._extract_api_metadata(self.openapi_spec)

        # Format schemas and other components for inclusion in the prompt
        formatted_schemas = json.dumps(self.schemas, cls=DateTimeEncoder)
        formatted_parameters = json.dumps(self.parameters, cls=DateTimeEncoder)
        formatted_responses = json.dumps(self.responses, cls=DateTimeEncoder)
        formatted_request_bodies = json.dumps(self.request_bodies, cls=DateTimeEncoder)

        # Create metadata section only if metadata is available
        metadata_section = ""
        if metadata:
            formatted_metadata = json.dumps(metadata, cls=DateTimeEncoder)
            metadata_section = f"USE API DATA TO THINK AND INFER MORE CONTEXT ABOUT THE COMPANY AND HOW USERS USE THEIR SERVICES WHEN CREATING WORKFLOWS \nAPI METADATA:\n{formatted_metadata}\n\n"

        # Format the user workflow section
        logger.info(f"Workflow descriptions received: {self.workflow_descriptions}")
        workflow_section = self.llm_service._format_user_workflow_section(
            self.workflow_descriptions
        )
        logger.debug(
            f"Formatted workflow section for prompt: '{workflow_section[:100]}...' (truncated)"
        )

        # Get the prompt template file path
        prompt_file = (
            pathlib.Path(__file__).parent / "prompts" / "direct_llm_arazzo_generation.prompt"
        )

        try:
            # Read the prompt template
            with open(prompt_file) as f:
                prompt_template = f.read()

            # Use string replace instead of format to avoid issues with JSON examples
            # that contain curly braces which can be misinterpreted as format placeholders
            prompt = prompt_template
            prompt = prompt.replace("{endpoints}", formatted_endpoints)
            prompt = prompt.replace("{schema_types}", formatted_schemas)
            prompt = prompt.replace("{parameters}", formatted_parameters)
            prompt = prompt.replace("{responses}", formatted_responses)
            prompt = prompt.replace("{requestBodies}", formatted_request_bodies)
            prompt = prompt.replace("{metadata_section}", metadata_section)
            prompt = prompt.replace("{user_workflows}", workflow_section)
            logger.debug(f"Final prompt after replacements: '{prompt[:200]}...' (truncated)")

            return prompt

        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}") from None

    def _extract_arazzo_from_response(self, response: str) -> dict[str, Any]:
        """Extract and parse the Arazzo specification from the LLM response.

        Args:
            response: The raw response from the LLM.

        Returns:
            The parsed Arazzo specification as a dictionary.
        """
        try:
            # Extract JSON between ```json and ``` markers
            if "```json" in response and "```" in response.split("```json", 1)[1]:
                json_str = response.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in response:
                # Try without the "json" language specifier
                parts = response.split("```", 2)
                if len(parts) >= 3:
                    json_str = parts[1].strip()
                    # If the first part looks like a language specifier, remove it
                    if json_str.startswith("json"):
                        json_str = json_str[4:].strip()
                else:
                    logger.error("Could not extract JSON from code block")
                    return {}
            else:
                # No code blocks, try to use the whole response
                json_str = response.strip()

            # Simple parsing
            try:
                arazzo_spec = json.loads(json_str)

                # Replace source description URL with input file URL
                if "sourceDescriptions" in arazzo_spec and isinstance(
                    arazzo_spec["sourceDescriptions"], list
                ):
                    for source in arazzo_spec["sourceDescriptions"]:
                        if "url" in source:
                            source["url"] = self.openapi_spec_url

                if "sourceDescriptions" in arazzo_spec and isinstance(
                    arazzo_spec["sourceDescriptions"], list
                ):
                    for source in arazzo_spec["sourceDescriptions"]:
                        if "name" in source:
                            source["name"] = "openapi_source"

                return arazzo_spec
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.debug(f"Extracted JSON string: {json_str[:200]}...")
                return {}

        except Exception as e:
            logger.error(f"Failed to extract Arazzo specification: {e}")
            return {}

    def to_yaml(self) -> str:
        """Convert the Arazzo specification to YAML.

        Returns:
            The Arazzo specification as a YAML string.
        """

        if not self.arazzo_spec:
            self.generate()

        if not self.arazzo_spec:
            return ""

        return ArazzoSerializer.to_yaml(self.arazzo_spec)

    def to_json(self) -> str:
        """Convert the Arazzo specification to JSON.

        Returns:
            The Arazzo specification as a JSON string.
        """

        if not self.arazzo_spec:
            self.generate()

        if not self.arazzo_spec:
            return ""

        return ArazzoSerializer.to_json(self.arazzo_spec)
