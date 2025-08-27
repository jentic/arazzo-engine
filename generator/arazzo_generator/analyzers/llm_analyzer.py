"""LLM-based workflow extraction for OpenAPI specifications.

This module contains the implementation of LLM-based workflow extraction
that uses large language models to identify and generate workflows from
OpenAPI specifications.
"""

from typing import Any

from arazzo_generator.analyzers.base_analyzer import BaseAnalyzer
from arazzo_generator.llm.litellm_service import LiteLLMService
from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)


class LLMAnalyzer(BaseAnalyzer):
    """Analyzes OpenAPI specifications to extract workflows using LLM-based approaches."""

    def __init__(
        self,
        endpoints: dict[str, dict],
        schemas: dict[str, Any],
        parameters: dict[str, Any],
        responses: dict[str, Any],
        request_bodies: dict[str, Any],
        spec: dict[str, Any] = None,
        relationships: dict | None = None,
        api_key: str | None = None,
        llm_model: str | None = None,
        llm_provider: str | None = None,
    ):
        """Initialize the LLM-based analyzer.

        Args:
            endpoints: Dictionary of endpoints from the OpenAPI spec
            schemas: Dictionary of schemas from the OpenAPI spec
            parameters: Dictionary of parameters from the OpenAPI spec
            responses: Dictionary of responses from the OpenAPI spec
            request_bodies: Dictionary of request bodies from the OpenAPI spec
            spec: The complete OpenAPI specification
            relationships: Optional dictionary of endpoint relationships
            api_key: API key for the LLM service (overrides config if provided)
            llm_model: LLM model to use (overrides config if provided)
            llm_provider: LLM provider to use (overrides config if provided)
        """
        super().__init__(endpoints, relationships)
        self.schemas = schemas
        self.parameters = parameters
        self.responses = responses
        self.request_bodies = request_bodies
        self.spec = spec

        # Initialize LLM service with provided config or use defaults from config
        llm_kwargs = {}
        if api_key is not None:
            llm_kwargs["api_key"] = api_key
        if llm_model is not None:
            llm_kwargs["llm_model"] = llm_model
        if llm_provider is not None:
            llm_kwargs["llm_provider"] = llm_provider

        self.llm_service = LiteLLMService(**llm_kwargs)

    def is_available(self) -> bool:
        """Check if the LLM service is available.

        Returns:
            True if the LLM service is available, False otherwise.
        """
        return self.llm_service.is_available()

    def analyze(self, user_workflow_descriptions: list[str] | None = None) -> list[dict[str, Any]]:
        """Analyze the OpenAPI specification to identify workflows using LLM.
        If user_workflow_descriptions is provided, it focuses the LLM on those specific workflows.

        Returns:
            A list of identified workflows.
        """
        if not self.is_available():
            logger.warning("LLM service not available. No workflows will be identified.")
            return []

        try:
            logger.info("Performing LLM-based workflow analysis")

            # Get LLM-generated workflows with spec metadata
            self.workflows = self.llm_service.analyze_endpoints(
                self.endpoints,
                self.schemas,
                self.parameters,
                self.responses,
                self.request_bodies,
                self.spec,  # Pass the full spec for metadata extraction
                user_workflow_descriptions=user_workflow_descriptions,  # Pass user descriptions
            )

            logger.info(f"LLM-based analysis identified {len(self.workflows)} workflows")
            [logger.info(f": {workflow['name']}") for workflow in self.workflows]
            return self.workflows

        except Exception as e:
            logger.error(f"LLM-based analysis failed: {e}")
            return []
