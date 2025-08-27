"""Base analyzer class for workflow extraction from OpenAPI specifications."""

from abc import ABC, abstractmethod
from typing import Any

from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAnalyzer(ABC):
    """Base class for all workflow analyzers.

    This abstract class defines the common interface that all analyzer
    implementations must follow. It provides a consistent way to analyze
    OpenAPI specifications and extract workflows.
    """

    def __init__(self, endpoints: dict[str, dict], relationships: dict | None = None):
        """Initialize the base analyzer.

        Args:
            endpoints: Dictionary of endpoints from the OpenAPI spec
            relationships: Optional dictionary of endpoint relationships
        """
        self.endpoints = endpoints
        self.relationships = relationships or {}
        self.workflows = []

    @abstractmethod
    def analyze(self) -> list[dict[str, Any]]:
        """Analyze the OpenAPI specification to identify workflows.

        This method should be implemented by subclasses to perform the
        actual analysis and workflow extraction.
        """
        pass

    def get_workflows(self) -> list[dict[str, Any]]:
        """Get the list of identified workflows.

        Returns:
            A list of dictionaries, where each dictionary represents a workflow.
        """
        return self.workflows
