"""Arazzo specification generator module."""

from typing import Any

from arazzo_generator.utils.logging import get_logger
from arazzo_generator.utils.serializer import ArazzoSerializer

from .components import ArazzoComponentsBuilder
from .output_mapping_validator import OutputMappingValidator
from .reference_validator import ReferenceValidator
from .workflow_builder import WorkflowBuilder

logger = get_logger(__name__)


class ArazzoGenerator:
    """Generator for creating Arazzo specifications from identified workflows.

    This class is responsible for converting identified workflows into an Arazzo
    specification according to the Arazzo 1.0 schema.
    """

    def __init__(
        self,
        workflows: list[dict[str, Any]],
        openapi_spec_url: str,
        endpoints: dict[str, dict[str, Any]],
        openapi_spec: dict[str, Any] = None,
    ):
        """Initialize the Arazzo generator.

        Args:
            workflows: List of identified workflows from the workflow analyzer.
            openapi_spec_url: URL to the original OpenAPI specification.
            endpoints: Dictionary of endpoints from the OpenAPI parser.
            openapi_spec: The full OpenAPI specification as a dictionary.
        """
        self.workflows = workflows
        self.openapi_spec_url = openapi_spec_url
        self.endpoints = endpoints
        self.openapi_spec = openapi_spec
        self.arazzo_spec = {}

    def generate(self) -> dict[str, Any]:
        """Generate an Arazzo specification from the identified workflows.

        Returns:
            The generated Arazzo specification as a dictionary.
            Returns None if no valid workflows are found.
        """
        # Check if there are any workflows to process
        if not self.workflows:
            logger.warning("No workflows provided. Cannot generate Arazzo specification.")
            return None

        self._init_arazzo_spec()
        self._add_source_descriptions()
        self._generate_workflows()

        # Check if any workflows were successfully created
        if not self.arazzo_spec["workflows"]:
            logger.warning("No valid workflows were created. Cannot generate Arazzo specification.")
            return None

        self._add_components()

        return self.arazzo_spec

    def to_yaml(self) -> str:
        """Convert the Arazzo specification to YAML.

        Returns:
            The Arazzo specification as a YAML string.
        """
        if not self.arazzo_spec:
            self.generate()

        # Generate YAML content
        return ArazzoSerializer.to_yaml(self.arazzo_spec)

    def to_json(self) -> str:
        """Convert the Arazzo specification to JSON.

        Returns:
            The Arazzo specification as a JSON string.
        """
        if not self.arazzo_spec:
            self.generate()

        # Generate JSON content with pretty formatting (indent)
        return ArazzoSerializer.to_json(self.arazzo_spec)

    def _init_arazzo_spec(self) -> None:
        """Initialize the Arazzo specification with required fields."""
        self.arazzo_spec = {
            "arazzo": "1.0.1",
            "info": {
                "title": "Jentic Generated Arazzo Specification",
                "version": "1.0.0",
                "description": "Automatically generated Arazzo specification from OpenAPI",
            },
            "sourceDescriptions": [],
            "workflows": [],
            "components": {},
        }

    def _add_source_descriptions(self) -> None:
        """Add source descriptions to the Arazzo specification using the OpenAPI spec URL.

        Always uses the openapi_spec_url that was passed during initialization,
        which will be the local file path or URL used to load the spec.
        """
        # Always use the openapi_spec_url that was passed during initialization
        source_url = str(self.openapi_spec_url)
        logger.debug(f"Using source URL: {source_url}")

        self.arazzo_spec["sourceDescriptions"] = [
            {"name": "openapi_source", "url": source_url, "type": "openapi"}
        ]

    def _generate_workflows(self) -> None:
        """Generate Arazzo workflows from the identified workflows."""
        workflow_builder = WorkflowBuilder(self.endpoints, self.openapi_spec)

        for workflow in self.workflows:
            try:
                logger.debug(f"Processing workflow: {workflow.get('name', 'unnamed')}")
                arazzo_workflow = workflow_builder.create_workflow(workflow)
                if arazzo_workflow:
                    # Validate and fix step references
                    logger.debug(
                        f"Validating step references for workflow: {arazzo_workflow.get('workflowId', 'unknown')}"
                    )
                    validator = ReferenceValidator()
                    arazzo_workflow = validator.validate_step_references(arazzo_workflow)

                    # Validate and fix output mappings
                    logger.debug(
                        f"Validating output mappings for workflow: {arazzo_workflow.get('workflowId', 'unknown')}"
                    )
                    arazzo_workflow = OutputMappingValidator.validate_output_mappings(
                        arazzo_workflow, self.openapi_spec, self.endpoints
                    )

                    self.arazzo_spec["workflows"].append(arazzo_workflow)
            except Exception as e:
                logger.error(f"Error generating workflow: {e}", exc_info=True)

    def _add_components(self) -> None:
        """Add components to the Arazzo specification."""
        components_dict = ArazzoComponentsBuilder().build_default_components()
        # Extract the inner components dictionary to avoid nesting
        self.arazzo_spec["components"] = components_dict["components"]
