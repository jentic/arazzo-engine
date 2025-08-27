"""
Batch processor for generating Arazzo workflows from multiple OpenAPI specifications.
"""

import os
import time
from datetime import datetime

from arazzo_generator.generator.generator_service import generate_arazzo
from arazzo_generator.utils.config import get_config, get_project_root
from arazzo_generator.utils.logging import get_logger

from .utils import get_openapi_files, get_output_path, write_summary_entry


class BatchProcessor:
    """Handles batch processing of OpenAPI specifications to generate Arazzo workflows."""

    def __init__(
        self,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        logs_dir: str | None = None,
        summary_file: str | None = None,
        max_retries: int = 3,
        save_logs: bool = True,
        output_format: str = "json",
    ):
        """
        Initialize the batch processor.

        Args:
            llm_provider: LLM provider to use (overrides config if provided)
            llm_model: Specific LLM model to use (overrides config if provided)
            logs_dir: Directory to save logs (overrides config if provided)
            summary_file: Path to the summary file
            max_retries: Maximum number of retries for failed specifications
            save_logs: If True, save LLM logs to batch_logs directory
        """
        # Store LLM configuration
        self.llm_provider = llm_provider
        self.llm_model = llm_model

        # Set up logging directory
        config = get_config()
        project_root = get_project_root()

        if llm_model and not llm_provider:
            raise ValueError("LLM model provided through CLI arg without LLM provider")

        if llm_provider and not llm_model:
            raise ValueError("LLM provider provided through CLI arg without LLM model")

        # Set provider (CLI arg > config)
        self.llm_provider = llm_provider or config.llm.llm_provider

        # Set model (CLI arg > config)
        self.llm_model = llm_model or config.llm.llm_model

        # Use provided logs_dir or fall back to configured logs directory
        if logs_dir is not None:
            self.logs_dir = str(logs_dir)
        else:
            self.logs_dir = str(project_root / config.logging.paths.logs_dir)

        self.max_retries = max_retries
        self.save_logs = save_logs
        self.output_format = output_format.lower()
        if self.output_format not in ("json", "yaml"):
            self.output_format = "json"  # Default to json if invalid format provided
        self.logger = get_logger(__name__)

        # Store summary file parameter - will be set up when processing starts
        self._summary_file_param = summary_file
        self.summary_file = None

    def _setup_summary_file(self):
        """Set up the summary file for this batch run if not already set up."""
        if self.summary_file is None:
            if self._summary_file_param is None:
                # Create timestamped summary file in batch_logs directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                config = get_config()
                project_root = get_project_root()
                batch_logs_dir = str(project_root / config.logging.paths.batch_logs_dir)
                summary_dir = os.path.join(batch_logs_dir, "summary_logs")

                # Create the summary directory if it doesn't exist
                os.makedirs(summary_dir, exist_ok=True)

                self.summary_file = os.path.join(summary_dir, f"batch_summary_{timestamp}.csv")
            else:
                self.summary_file = self._summary_file_param
                # Ensure the directory exists for custom summary file paths too
                os.makedirs(os.path.dirname(os.path.abspath(self.summary_file)), exist_ok=True)

            self.logger.info(f"Summary will be written to: {self.summary_file}")

    def generate_arazzo(
        self,
        openapi_path,
        output_path,
        llm_provider=None,
        llm_model=None,
        skip_existing=True,
        save_logs=True,
        logs_dir=None,
        direct_llm=False,
    ):
        """
        Generate an Arazzo workflow file from an OpenAPI specification.

        Args:
        openapi_path: Path to the OpenAPI specification file
        output_path: Path where the Arazzo workflow file should be saved
        llm_provider: LLM provider to use (gemini, anthropic, or openai)
        llm_model: Specific LLM model to use
        skip_existing: If True, skip processing if output file already exists
        save_logs: If True, save LLM logs to batch_logs directory
        logs_dir: Directory to save LLM logs
        direct_llm: If True, use direct LLM generation

        Returns:
        True if successful, False otherwise
        """
        # Use configurable logs directory if none provided
        if logs_dir is None:
            config = get_config()
            project_root = get_project_root()
            logs_dir = str(project_root / config.logging.paths.logs_dir)

        logger = get_logger(__name__)
        try:
            self.logger.info(f"Generating Arazzo workflow from {openapi_path}")

            provider = llm_provider if llm_provider is not None else self.llm_provider
            model = llm_model if llm_model is not None else self.llm_model

            arazzo_spec, arazzo_content, is_valid, validation_errors, fallback_used = (
                generate_arazzo(
                    openapi_path,
                    format=self.output_format,  # Use the specified output format
                    output=output_path,
                    validate_spec=True,
                    direct_llm=direct_llm,
                    llm_provider=provider,
                    llm_model=model,
                )
            )

            if arazzo_content is None or not is_valid:
                logger.error(f"Failed to generate valid Arazzo workflow for {openapi_path}")
                if validation_errors:
                    logger.error(f"Validation errors: {validation_errors}")
                return False

            # Write the generated content to the output file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(arazzo_content)

            self.logger.info(f"Successfully generated Arazzo workflow: {output_path}")

            if not is_valid and validation_errors:
                logger.warning(f"Generated workflow has validation issues: {validation_errors}")

            return True

        except Exception as e:
            logger.error(f"Error generating Arazzo workflow for {openapi_path}: {str(e)}")
            return False

    def _extract_vendor_api_from_path(self, spec_path: str) -> tuple[str, str]:
        """Extract vendor and API name from path."""
        path_parts = spec_path.split(os.sep)
        vendor_index = path_parts.index("openapi") + 1
        vendor_name = path_parts[vendor_index]
        api_name = path_parts[vendor_index + 1]
        return vendor_name, api_name

    def process_single_spec(
        self,
        spec_path,
        llm_provider,
        skip_existing=True,
        save_logs=True,
        logs_dir=None,
        direct_llm=False,
        llm_model=None,
    ):
        """Process a single OpenAPI specification file."""
        # Use configurable logs directory if none provided
        if logs_dir is None:
            config = get_config()
            project_root = get_project_root()
            logs_dir = str(project_root / config.logging.paths.logs_dir)

        start_time = time.time()

        # Extract vendor and api names from path
        filename = os.path.basename(spec_path)
        vendor_name = filename.split(".")[0]  # e.g., "discord.openapi.json" -> "discord"
        api_name = "main"  # Default for single files

        if not os.path.exists(spec_path):
            self.logger.error(f"Specification file not found: {spec_path}")
            summary_data = {
                "vendor": vendor_name,
                "api": api_name,
                "spec_path": spec_path,
                "output_path": "",
                "status": "error",
                "duration": time.time() - start_time,
                "error": "Specification file not found",
            }
            return False, summary_data

        # Get output path with the specified format
        output_path = get_output_path(spec_path, output_format=self.output_format)
        self.logger.info(f"Processing spec: {spec_path}")
        self.logger.info(f"Output will be saved to: {output_path}")

        # Check if file already exists and we should skip
        if skip_existing and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                self.logger.info(
                    f"Arazzo workflow exists: {output_path} ({file_size} bytes). Skipping."
                )
                summary_data = {
                    "vendor": vendor_name,
                    "api": api_name,
                    "spec_path": spec_path,
                    "output_path": output_path,
                    "status": "skipped",
                    "duration": time.time() - start_time,
                }
                return True, summary_data

        try:
            success = self.generate_arazzo(
                spec_path,
                output_path,
                llm_provider=llm_provider,
                llm_model=llm_model,
                skip_existing=skip_existing,
                save_logs=save_logs,
                logs_dir=logs_dir,
                direct_llm=direct_llm,
            )
            error_message = ""
        except Exception as e:
            success = False
            error_message = str(e)
            self.logger.error(f"Unexpected error processing {spec_path}: {error_message}")

        # Create summary data
        summary_data = {
            "vendor": vendor_name,
            "api": api_name,
            "spec_path": spec_path,
            "output_path": output_path,
            "status": "success" if success else "error",
            "duration": time.time() - start_time,
            "error": error_message if not success else "",
        }

        return success, summary_data

    def process_all(self, force: bool = False, delay_between_specs: int = 0) -> tuple[int, int]:
        """
        Process all OpenAPI specifications.

        Args:
            force: Whether to force regeneration even if output exists
            delay_between_specs: Delay in seconds between processing specs

        Returns:
            Tuple of (success_count, total_count)
        """
        self.logger.info("Processing all OpenAPI specifications")

        # Get all OpenAPI specification files
        spec_files = get_openapi_files()

        if not spec_files:
            self.logger.warning("No OpenAPI specification files found")
            return 0, 0

        self.logger.info(f"Found {len(spec_files)} OpenAPI specification files")

        # Process all specs using process_spec_list
        return self.process_spec_list(spec_files, force, delay_between_specs)

    def process_spec_list(
        self, spec_list: list[str], force: bool = False, delay_between_specs: int = 20
    ) -> tuple[int, int]:
        """
        Process OpenAPI specifications from a list of paths.

        Args:
            spec_list: List of paths to OpenAPI specs
            force: Whether to force regeneration even if output exists
            delay_between_specs: Delay in seconds between processing files

        Returns:
            Tuple of (success_count, total_count)
        """
        # Set up summary file for this batch run
        self._setup_summary_file()

        self.logger.info(f"Processing {len(spec_list)} OpenAPI specifications")

        success_count = 0
        for i, spec_path in enumerate(spec_list):
            # Convert force flag to skip_existing (force=True means skip_existing=False)
            skip_existing = not force
            success, summary_data = self.process_single_spec(
                spec_path,
                llm_provider=self.llm_provider,
                skip_existing=skip_existing,
                save_logs=self.save_logs,
                logs_dir=self.logs_dir,
                direct_llm=False,
                llm_model=self.llm_model,
            )
            if success and summary_data.get("status") in ["success", "skipped"]:
                success_count += 1

            # Write summary entry
            if self.summary_file:
                write_summary_entry(
                    self.summary_file,
                    summary_data["vendor"],
                    summary_data["api"],
                    summary_data["spec_path"],
                    summary_data["output_path"],
                    summary_data["status"],
                    summary_data["duration"],
                )

            # Add delay between specs (except for the last one)
            if i < len(spec_list) - 1 and delay_between_specs > 0:
                self.logger.info(f"Waiting {delay_between_specs}s before next file...")
                time.sleep(delay_between_specs)

        self.logger.info(
            f"Processed {success_count} of {len(spec_list)} specifications successfully"
        )
        return success_count, len(spec_list)
