"""Base analyzer class for workflow extraction from OpenAPI specifications."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAnalyzer(ABC):
    """Base class for all workflow analyzers.

    This abstract class defines the common interface that all analyzer
    implementations must follow. It provides a consistent way to analyze
    OpenAPI specifications and extract workflows.
    """

    def __init__(
        self, endpoints: Dict[str, Dict], relationships: Optional[Dict] = None
    ):
        """Initialize the base analyzer.

        Args:
            endpoints: Dictionary of endpoints from the OpenAPI spec
            relationships: Optional dictionary of endpoint relationships
        """
        self.endpoints = endpoints
        self.relationships = relationships or {}
        self.workflows = []

    @abstractmethod
    def analyze(self) -> List[Dict[str, Any]]:
        """Analyze the OpenAPI specification to identify workflows.

        This method must be implemented by all subclasses to perform
        the actual workflow identification logic.

        Returns:
            A list of identified workflows.
        """
        pass

    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get the list of identified workflows.

        Returns:
            The list of workflows identified by the analyzer.
        """
        return self.workflows
