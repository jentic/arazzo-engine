"""Project-wide custom exceptions used across the Arazzo generator codebase."""


class ArazzoError(Exception):
    """Base class for predictable generator-level failures."""


class InvalidUserWorkflowError(ArazzoError):
    """Raised when the requested workflows cannot be built from the OpenAPI spec.

    Args:
        requested_workflows (list[str]): list of requested workflow descriptions.
    """

    def __init__(self, requested_workflows=None):
        self.requested_workflows = requested_workflows or []
        super().__init__(
            "No valid workflows identified for this API. The generated spec will contain an empty workflows list."
        )


class SpecValidationError(ArazzoError):
    """
    Raised when the generated Arazzo specification fails schema validation.

    Args:
        validation_errors (list[str]): list of human-readable validation error messages.
    """

    def __init__(self, validation_errors: list[str]):
        self.validation_errors = validation_errors
        super().__init__("Arazzo specification failed validation")
