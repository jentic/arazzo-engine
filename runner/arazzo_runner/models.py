#!/usr/bin/env python3
"""
Arazzo Runner Data Models

This module defines the data models and enums used by the Arazzo Runner.
"""

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

OpenAPIDoc = dict[str, Any]
ArazzoDoc = dict[str, Any]


class StepStatus(Enum):
    """Status of a workflow step execution"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class ActionType(Enum):
    """Type of action to take after a step execution"""

    CONTINUE = "continue"  # Continue to next step
    END = "end"  # End workflow
    GOTO = "goto"  # Go to another step or workflow
    RETRY = "retry"  # Retry the current step


class WorkflowExecutionStatus(StrEnum):
    """Represents the status strings returned by Arazzo Runner execution logic."""

    WORKFLOW_COMPLETE = "workflow_complete"
    ERROR = "error"
    GOTO_WORKFLOW = "goto_workflow"
    GOTO_STEP = "goto_step"
    RETRY = "retry"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


@dataclass
class WorkflowExecutionResult:
    """Represents the result of a workflow execution

    This class models the structure of the result returned by the execute_workflow method.

    Attributes:
        status: The status of the workflow execution (e.g., WORKFLOW_COMPLETE, ERROR)
        workflow_id: The ID of the executed workflow
        outputs: The outputs produced by the workflow
        step_outputs: The outputs from each step in the workflow
        inputs: The original inputs provided to the workflow
        error: Optional error message if the workflow execution failed
    """

    status: WorkflowExecutionStatus
    workflow_id: str
    outputs: dict[str, Any] = field(default_factory=dict)
    step_outputs: dict[str, dict[str, Any]] | None = None
    inputs: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class ExecutionState:
    """Represents the current execution state of a workflow"""

    workflow_id: str
    current_step_id: str | None = None
    inputs: dict[str, Any] = None
    step_outputs: dict[str, dict[str, Any]] = None
    workflow_outputs: dict[str, Any] = None
    dependency_outputs: dict[str, dict[str, Any]] = None
    status: dict[str, StepStatus] = None
    runtime_params: Optional["RuntimeParams"] = None

    def __post_init__(self):
        """Initialize default values"""
        if self.inputs is None:
            self.inputs = {}
        if self.step_outputs is None:
            self.step_outputs = {}
        if self.workflow_outputs is None:
            self.workflow_outputs = {}
        if self.dependency_outputs is None:
            self.dependency_outputs = {}
        if self.status is None:
            self.status = {}


class ServerVariable(BaseModel):
    """Represents a variable for server URL template substitution."""

    description: str | None = None
    default_value: str | None = Field(None, alias="default")
    enum_values: list[str] | None = Field(None, alias="enum")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ServerConfiguration(BaseModel):
    """Represents an API server configuration with a templated URL and variables."""

    url_template: str = Field(alias="url")
    description: str | None = None
    variables: dict[str, ServerVariable] = Field(default_factory=dict)
    api_title_prefix: str | None = None  # Derived from spec's info.title

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class RuntimeParams(BaseModel):
    """
    Container for all runtime parameters that may influence workflow or operation execution.
    """

    servers: dict[str, str] | None = Field(
        default=None, description="Server variable overrides for server resolution."
    )
