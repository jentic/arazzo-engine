"""Command-line interface for the OpenAPI to Arazzo generator."""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from arazzo_generator.batch.batch_generator import BatchProcessor
from arazzo_generator.generator.generator_service import generate_arazzo, validate_arazzo
from arazzo_generator.utils.logging import get_logger, setup_logging

# Load environment variables from .env file
load_dotenv()

# Initialize logger
logger = get_logger(__name__)


@click.group()
@click.version_option()
def cli():
    """Generate Arazzo workflows from OpenAPI specifications."""
    pass


@cli.command()
@click.argument("url")
@click.option(
    "--output",
    "-o",
    help="Output file path for the generated Arazzo spec. If not provided, the spec will be printed to stdout.",
    type=click.Path(),
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json"]),
    default="json",
    help="Output format for the generated Arazzo spec. Default is yaml.",
)
@click.option(
    "--validate-spec/--no-validate-spec",
    default=True,
    help="Validate the generated Arazzo spec.",
    show_default=True,
)
@click.option(
    "--direct-llm/--no-direct-llm",
    default=False,
    help="Enable/disable direct LLM generation of Arazzo specification, bypassing the generator code.",
)
@click.option(
    "--api-key",
    help="API key for LLM service. If not provided, will use the appropriate environment variable based on the provider.",
    default=None,
)
@click.option(
    "--llm-model",
    help="Override the LLM model to use for analysis. If not provided, uses the model from config.toml.",
    default=None,
)
@click.option(
    "--llm-provider",
    help="Override the LLM provider to use. If not provided, uses the provider from config.toml.",
    default=None,
)
@click.option(
    "--workflow-descriptions",
    multiple=True,
    help="User-requested workflow description to generate. Repeat for multiple descriptions.",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose output.")
def generate(
    url: str,
    output: str | None,
    format: str,
    validate_spec: bool,
    verbose: bool,
    direct_llm: bool,
    api_key: str | None,
    llm_model: str | None,
    llm_provider: str | None,
    workflow_descriptions: tuple[str],
):
    """Generate an Arazzo spec from an OpenAPI spec URL.

    URL is the URL to the OpenAPI specification.
    """
    logger.info(f"Starting Arazzo generation from: {url}")
    logger.debug(
        f"Options - format: {format}, validate_spec: {validate_spec}, direct_llm: {direct_llm}"
    )

    try:
        # Configure logging level based on verbose flag
        log_level = "DEBUG" if verbose else None
        setup_logging(log_level=log_level)

        # Call the service function to generate the Arazzo specification
        arazzo_spec, arazzo_content, is_valid, validation_errors, fallback_used = generate_arazzo(
            url=url,
            output=output,
            format=format,
            validate_spec=validate_spec,
            direct_llm=direct_llm,
            llm_model=llm_model,
            llm_provider=llm_provider,
            workflow_descriptions=(list(workflow_descriptions) if workflow_descriptions else None),
        )

        # Log fallback warning if used when workflow_descriptions were provided and failed to generate valid workflows
        if fallback_used:
            logger.warning(
                "Initial generation using provided workflow descriptions failed. Generator retried without those descriptions and succeeded"
            )

        # Handle validation errors
        if not is_valid and validate_spec:
            logger.error("Generated Arazzo spec is not valid")
            for error in validation_errors:
                logger.error(f"Validation error: {error}")
            if output:
                logger.warning("Saving invalid Arazzo spec anyway")

        # Output Arazzo spec
        if output and arazzo_content:
            logger.info(f"Writing Arazzo spec to {output}")
            with open(output, "w") as f:
                f.write(arazzo_content)
        elif arazzo_content:
            print(arazzo_content)
        else:
            logger.error("No Arazzo content generated")
            sys.exit(1)

        logger.info("Arazzo generation completed successfully")

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.argument("file", type=click.Path(exists=True))
def validate(file: str):
    """Validate an Arazzo spec file.

    FILE is the path to the Arazzo specification file (YAML or JSON).
    """
    logger.info(f"Validating Arazzo specification: {file}")

    try:
        # Call the service function to validate the Arazzo specification
        is_valid, validation_errors, _ = validate_arazzo(file)

        if is_valid:
            logger.info("✅ Arazzo spec is valid")
            print("✅ Arazzo specification is valid!")
        else:
            logger.error("❌ Arazzo spec is not valid")
            print("❌ Arazzo specification is not valid. Errors:")
            for error in validation_errors:
                logger.debug(f"Validation error: {error}")
                print(f"- {error}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--llm-provider",
    type=click.Choice(["gemini", "anthropic", "openai"]),
    help="LLM provider to use (must be used with --llm-model)",
)
@click.option("--llm-model", help="Specific LLM model to use (must be used with --llm-provider)")
@click.option("--delay", default=20, type=int, help="Delay in seconds between processing files")
@click.option("--summary-file", help="File to write processing summary")
@click.option(
    "--force/--skip-existing",
    default=False,
    help="Force regeneration even if workflow exists",
)
@click.option("--save-logs/--no-logs", default=True, help="Save LLM logs to logs directory")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--spec-list", help="Process specifications from a file list")
@click.option("--all", is_flag=True, help="Process all specs in the directory")
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Output format (default: json)",
)
def batch(
    llm_provider,
    llm_model,
    delay,
    summary_file,
    force,
    save_logs,
    verbose,
    spec_list,
    all,
    format,
):
    """Generate Arazzo workflows from OpenAPI specifications in batch."""
    # Setup logging
    if verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
        setup_logging()
    logger.info("Starting batch processing of OpenAPI specifications")

    # Create processor with LLM config only if both provider and model are provided
    processor_kwargs = {
        "summary_file": summary_file,
        "save_logs": save_logs,
        "output_format": format,
    }

    # Only add LLM config if both provider and model are provided
    if llm_provider is not None or llm_model is not None:
        if llm_provider is None or llm_model is None:
            logger.error("Both --llm-provider and --llm-model must be specified if either is used")
            sys.exit(1)
        processor_kwargs.update(
            {
                "llm_provider": llm_provider,
                "llm_model": llm_model,
            }
        )

    # Create processor
    processor = BatchProcessor(**processor_kwargs)

    # Determine processing mode
    if spec_list:
        logger.info(f"Processing specs from list: {spec_list}")

        spec_list_path = Path(spec_list)
        if not spec_list_path.exists():
            logger.error(f"Spec list file not found: {spec_list_path}")
            sys.exit(1)

        specs = []
        with open(spec_list_path) as f:
            specs = [line.strip() for line in f if line.strip()]

        logger.info(f"Found {len(specs)} specifications in spec list file")
        success_count, total_count = processor.process_spec_list(
            specs,
            force=force,
            delay_between_specs=delay,
        )
        logger.info(f"Processed {success_count}/{total_count} specifications from list")

    elif all:
        logger.info("Processing all specifications")
        success_count, total_count = processor.process_all(
            force=force,
            delay_between_specs=delay,
        )
        logger.info(f"Processed {success_count}/{total_count} specifications")

    else:
        logger.error("No processing mode specified. Use --spec-list or --all")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
