"""Workflow manager module for coordinating workflow analysis.

This module contains the WorkflowManager class that coordinates the workflow
analysis process.
"""

from typing import Any

from arazzo_generator.utils.logging import get_logger

from .llm_analyzer import LLMAnalyzer

logger = get_logger(__name__)


class WorkflowAnalysisManager:
    """Manager for coordinating workflow analysis.

    This class is responsible for initializing the LLMAnalyzer and running the analysis process.
    """

    def __init__(
        self,
        spec: dict[str, dict[str, Any]],
        endpoints: dict[str, dict[str, Any]],
        schemas: dict[str, Any],
        parameters: dict[str, Any],
        responses: dict[str, Any],
        request_bodies: dict[str, Any],
        api_key: str | None = None,
        llm_model: str | None = None,
        llm_provider: str | None = None,
        workflow_descriptions: list[str] | None = None,
    ):
        """Initialize the workflow manager.

        Args:
            spec: The complete OpenAPI specification
            endpoints: Dictionary of endpoints from the OpenAPI spec
            schemas: Dictionary of schemas from the OpenAPI spec
            parameters: Dictionary of parameters from the OpenAPI spec
            responses: Dictionary of responses from the OpenAPI spec
            request_bodies: Dictionary of request bodies from the OpenAPI spec
            api_key: API key for the LLM service (overrides config if provided)
            llm_model: LLM model to use (overrides config if provided)
            llm_provider: LLM provider to use (overrides config if provided)
            workflow_descriptions: List of user-provided workflow descriptions
        """
        self.spec = spec
        self.endpoints = endpoints
        self.schemas = schemas
        self.parameters = parameters
        self.responses = responses
        self.request_bodies = request_bodies
        self.workflow_descriptions = workflow_descriptions

        # Store LLM configuration
        self.api_key = api_key
        self.llm_model = llm_model
        self.llm_provider = llm_provider

        # Initialize relationships dictionary (used by analyzers)
        self.relationships = {}

        # Initialize workflows list
        self.workflows = []

        # Initialize analyzers
        self.llm_analyzer = None

        self.llm_analyzer = LLMAnalyzer(
            endpoints=self.endpoints,
            schemas=self.schemas,
            parameters=self.parameters,
            responses=self.responses,
            request_bodies=self.request_bodies,
            spec=self.spec,
            relationships=self.relationships,
            api_key=self.api_key,
            llm_model=self.llm_model,
            llm_provider=self.llm_provider,
        )

        # Check if LLM service is available
        if not self.llm_analyzer.is_available():
            logger.warning("LLM service not available. Disabling LLM-based analysis.")
            self.llm_analyzer = None

    def analyze(self) -> list[dict[str, Any]]:
        """Analyze the OpenAPI specification to identify workflows.

        This method coordinates the analysis process, running the appropriate
        analyzers and combining their results.

        Returns:
            A list of identified workflows.
        """
        # Initialize empty workflows list
        self.workflows = []
        llm_workflows = []

        # Step 1: Perform LLM-based analysis
        if self.llm_analyzer:
            logger.info("Performing LLM-based workflow analysis")
            llm_workflows = self.llm_analyzer.analyze(
                user_workflow_descriptions=self.workflow_descriptions
            )

            if llm_workflows:
                logger.info(f"LLM-based analysis identified {len(llm_workflows)} workflows")
            else:
                logger.info("LLM-based analysis did not identify any workflows")

        if llm_workflows:
            self.workflows.extend(llm_workflows)

        # Step 2: Remove duplicates based on name
        self._remove_duplicates()

        # Step 3: Rank the combined workflows
        self._rank_workflows()

        logger.info(f"LLM-based analysis identified {len(self.workflows)} workflows")
        return self.workflows

    def _remove_duplicates(self) -> None:
        """Remove duplicate workflows based on name."""
        seen_names = set()
        unique_workflows = []

        for workflow in self.workflows:
            name = workflow.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                unique_workflows.append(workflow)

        self.workflows = unique_workflows

    def _rank_workflows(self) -> None:
        """Rank identified workflows based on usefulness and complexity."""
        # Adjust ranks based on various factors
        for workflow in self.workflows:
            # Increase rank for workflows with more operations
            num_operations = len(workflow.get("operations", []))
            if num_operations > 3:
                workflow["rank"] = min(10, workflow.get("rank", 0) + 1)

            # Decrease rank for overly complex workflows
            if num_operations > 5:
                workflow["rank"] = max(1, workflow.get("rank", 0) - 1)

            # Prioritize by workflow type
            workflow_type = workflow.get("type", "")
            if workflow_type == "auth":
                # Auth workflows are highest priority
                workflow["rank"] = max(workflow.get("rank", 0), 9)
            elif workflow_type == "crud":
                # CRUD workflows are high priority
                workflow["rank"] = max(workflow.get("rank", 0), 7)
            elif workflow_type == "process":
                # Process workflows are medium-high priority
                workflow["rank"] = max(workflow.get("rank", 0), 5)
            elif workflow_type == "group":
                # Grouped workflows are medium priority
                workflow["rank"] = max(workflow.get("rank", 0), 3)
            elif workflow_type == "basic":
                # Basic workflows are lowest priority
                workflow["rank"] = min(workflow.get("rank", 0), 1)

        # Sort workflows by rank
        self.workflows.sort(key=lambda w: w.get("rank", 0), reverse=True)
