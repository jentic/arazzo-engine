"""Core generator service for Arazzo specifications.

This module contains the core business logic for generating Arazzo specifications
from OpenAPI specifications, separated from interface concerns.
"""

import json
import logging
import time
from typing import Any

from arazzo_generator.analyzers.workflow_analysis_manager import WorkflowAnalysisManager
from arazzo_generator.generator.arazzo_generator import ArazzoGenerator
from arazzo_generator.llm.direct_arazzo_generator import DirectArazzoGenerator
from arazzo_generator.parser.openapi_parser import OpenAPIParser
from arazzo_generator.utils.exceptions import InvalidUserWorkflowError, SpecValidationError
from arazzo_generator.utils.logging import get_logger
from arazzo_generator.utils.serializer import ArazzoSerializer
from arazzo_generator.validator.arazzo_validator import ArazzoValidator

logger = get_logger(__name__)


def generate_arazzo(
    url: str,
    output: str | None = None,
    format: str = "json",
    validate_spec: bool = True,
    direct_llm: bool = False,
    api_key: str | None = None,
    llm_model: str | None = None,
    llm_provider: str | None = None,
    verbose: bool = False,
    workflow_descriptions: list[str] | None = None,
    _fallback_attempt: bool = False,  # Internal flag to prevent infinite recursion on fallback
) -> tuple[dict[str, Any], str, bool, list[str], bool]:
    """
    Core business logic for generating Arazzo specifications.

    Args:
        url: URL to the OpenAPI specification
        output: Output file path for the generated Arazzo spec.
        format: Output format ("json" or "yaml")
        validate_spec: Whether to validate the generated spec
        direct_llm: Enable direct LLM generation of Arazzo specification
        api_key: API key for the LLM service
        llm_model: LLM model to use (overrides config if provided)
        llm_provider: LLM provider to use (overrides config if provided)
        verbose: Enable verbose logging
        workflow_descriptions: Optional list of workflow descriptions (as strings) to guide the generator in creating specific workflows requested by the user. If provided, the generator will attempt to create only these workflows using the OpenAPI spec.

    Returns:
        Tuple containing:
        - The Arazzo spec as a dictionary (or None if generation failed)
        - The serialized content (JSON/YAML) (or None if generation failed)
        - Validation result (True if valid)
        - List of validation errors (empty if valid)
        - Whether fallback logic was used (True if fallback was used)
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse OpenAPI spec
    logger.info(f"Parsing OpenAPI spec from {url}")
    parser = OpenAPIParser(url)
    spec = parser.fetch_spec()
    endpoints = parser.get_endpoints()
    schemas = parser.get_schemas()
    parameters = parser.get_parameters()
    responses = parser.get_responses()
    request_bodies = parser.get_request_bodies()

    logger.debug(f"Found {len(endpoints)} endpoints")

    arazzo_spec = None
    arazzo_content = None
    validation_errors = []
    is_valid = True

    # Check if direct LLM generation is enabled
    if direct_llm:
        logger.info("Using direct LLM generation for Arazzo specification")

        # Initialize direct generator with LLM config
        direct_generator = DirectArazzoGenerator(
            openapi_spec_url=url,
            endpoints=endpoints,
            schemas=schemas,
            parameters=parameters,
            responses=responses,
            request_bodies=request_bodies,
            openapi_spec=spec,
            api_key=api_key,
            llm_model=llm_model,
            llm_provider=llm_provider,
            workflow_descriptions=workflow_descriptions,
        )

        # Check if LLM service is available
        if not direct_generator.is_available():
            logger.error("LLM service not available. Cannot use direct LLM generation.")
            logger.info("Falling back to standard generation process.")
            direct_llm = False
        else:
            # Generate Arazzo spec directly using LLM
            arazzo_spec = direct_generator.generate()

            if not arazzo_spec:
                logger.error(
                    "Direct LLM generation failed. Falling back to standard generation process."
                )
                direct_llm = False

    # Standard generation if direct generation not used or failed
    if not direct_llm:
        # Initialize workflow analysis manager
        logger.info("Analyzing API for workflows")
        analysis_manager = WorkflowAnalysisManager(
            endpoints=endpoints,
            schemas=schemas,
            parameters=parameters,
            responses=responses,
            request_bodies=request_bodies,
            spec=spec,
            api_key=api_key,
            llm_model=llm_model,
            llm_provider=llm_provider,
        )
        workflows = analysis_manager.analyze()

        # If user requested specific workflows but none could be generated, raise domain exception
        if not workflows:
            raise InvalidUserWorkflowError(workflow_descriptions)
        else:
            logger.info(f"Identified {len(workflows)} workflows")

        # Generate Arazzo spec
        logger.info("Generating Arazzo spec")
        generator = ArazzoGenerator(workflows, url, endpoints, spec)
        arazzo_spec = generator.generate()

        # Exit or fallback if no valid workflows were found
        if arazzo_spec is None:
            if workflow_descriptions and not _fallback_attempt:
                # Allow a 60 second sleep time after initial generation attempt (with custom workflow descriptions)
                # Retry with a second generation attempt (without custom descriptions)
                # 60 seconds to avoid token quota limits of LLMs
                wait_seconds = 60
                logger.warning(
                    "No valid workflows found with custom workflow descriptions. "
                    "Waiting %s seconds then retrying once without custom descriptions.",
                    wait_seconds,
                )
                logger.info("Sleeping for 60 seconds...")
                time.sleep(wait_seconds)
                logger.info("Sleep done. Retrying now without workflow_descriptions.")
                return generate_arazzo(
                    url=url,
                    output=output,
                    format=format,
                    validate_spec=validate_spec,
                    direct_llm=direct_llm,
                    api_key=api_key,
                    llm_model=llm_model,
                    llm_provider=llm_provider,
                    verbose=verbose,
                    workflow_descriptions=None,
                    _fallback_attempt=True,
                )
            logger.error("No valid workflows were found. Cannot generate Arazzo specification.")
            return (
                None,
                None,
                False,
                ["No valid workflows were found"],
                _fallback_attempt,
            )

    # Validate Arazzo spec
    if validate_spec and arazzo_spec:
        logger.info("Validating Arazzo spec")
        validator = ArazzoValidator()
        is_valid = validator.validate(arazzo_spec)

        if not is_valid:
            validation_errors = validator.get_validation_errors(arazzo_spec)
            raise SpecValidationError(validator.get_validation_errors(arazzo_spec))

    # Prepare output format
    if arazzo_spec:
        if format == "yaml":
            arazzo_content = ArazzoSerializer.get_arazzo_in_target_format(arazzo_spec, "yaml")
        else:  # json format
            arazzo_content = ArazzoSerializer.get_arazzo_in_target_format(arazzo_spec, "json")

    # Return result (even if spec is None)
    return arazzo_spec, arazzo_content, is_valid, validation_errors, _fallback_attempt


def validate_arazzo(
    file_path: str, verbose: bool = False
) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Validate an existing Arazzo specification file.

    Args:
        file_path: Path to the Arazzo specification file
        verbose: Enable verbose logging

    Returns:
        Tuple containing:
        - Validation result (True if valid)
        - List of validation errors (empty if valid)
        - The loaded Arazzo spec as a dictionary
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Validating Arazzo spec from {file_path}")

    # Determine file format based on extension
    is_json = file_path.lower().endswith(".json")

    # Load Arazzo spec
    try:
        with open(file_path) as f:
            if is_json:
                arazzo_spec = json.loads(f.read())
            else:
                import yaml

                arazzo_spec = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading file: {e}")
        return False, [f"Error loading file: {e}"], None

    # Validate Arazzo spec
    validator = ArazzoValidator()
    is_valid = validator.validate(arazzo_spec)

    if is_valid:
        logger.info("Arazzo spec is valid")
        return True, [], arazzo_spec
    else:
        logger.error("Arazzo spec is not valid")
        validation_errors = validator.get_validation_errors(arazzo_spec)
        return False, validation_errors, arazzo_spec
