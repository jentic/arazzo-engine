"""
Utility functions for batch processing of OpenAPI specifications.
"""

import glob
import os
from datetime import datetime

from arazzo_generator.utils.config import get_config, get_project_root
from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)


def get_openapi_files():
    """
    Get a list of OpenAPI specification files from the repository.
    Finds all files named 'openapi.json' or ending with 'openapi.json'.

    Returns:
        List of file paths to OpenAPI specifications
    """
    config = get_config()
    project_root = get_project_root()
    base_path = str(project_root / config.batch.paths.openapi_dir)
    logger.debug(f"Using openapi_dir: {base_path}")

    # Search for files ending with 'openapi.json' (includes exact matches)
    search_pattern = os.path.join(base_path, "**", "*openapi.json")
    files = glob.glob(search_pattern, recursive=True)

    logger.info(f"Found {len(files)} OpenAPI specification files in {base_path}")
    return files


def get_output_path(openapi_path, output_format="json"):
    """
    Generate the output path for an Arazzo workflow file based on the OpenAPI spec path.

    Args:
        openapi_path: Path to the OpenAPI specification file
        output_format: Output format, either 'json' or 'yaml' (default: 'json')

    Returns:
        Path where the Arazzo workflow file should be saved
    """
    # Ensure output format is either json or yaml
    output_format = output_format.lower()
    if output_format not in ("json", "yaml"):
        output_format = "json"  # Default to json if invalid format provided
    # Extract vendor name from the path
    path_parts = openapi_path.split(os.sep)

    # Try to find "openapi" in the path for standard structure
    if "openapi" in path_parts:
        openapi_index = path_parts.index("openapi")

        # Check if there are enough parts after "openapi" for vendor/api structure
        if openapi_index + 2 < len(path_parts):
            # Standard structure: openapi/vendor.com/api-name/openapi.json
            vendor_name = path_parts[openapi_index + 1]
            api_name = path_parts[openapi_index + 2]
            workflow_dir = create_workflow_dir(vendor_name)

            if api_name == "main":
                # For main APIs, use vendor name directly
                return os.path.join(workflow_dir, f"workflows.arazzo.{output_format}")
            else:
                # For non-main APIs, use vendor~api-name format
                api_dir = f"{vendor_name}~{api_name}"
                workflow_dir = create_workflow_dir(api_dir)
                return os.path.join(workflow_dir, f"workflows.arazzo.{output_format}")
        else:
            # Flat structure: openapi/vendor.openapi.json
            filename = os.path.basename(openapi_path)
            # Extract vendor name from filename (e.g., "discord.openapi.json" -> "discord")
            if ".openapi.json" in filename:
                vendor_name = filename.replace(".openapi.json", "")
            else:
                # Fallback: use first part of filename
                vendor_name = filename.split(".")[0]

            workflow_dir = create_workflow_dir(vendor_name)
            return os.path.join(workflow_dir, f"workflows.arazzo.{output_format}")
    else:
        # For non-standard paths, extract vendor from filename
        filename = os.path.basename(openapi_path)
        # Remove file extension and extract vendor name
        vendor_name = filename.split(".")[0]

        workflow_dir = create_workflow_dir(vendor_name)
        return os.path.join(workflow_dir, f"workflows.arazzo.{output_format}")


def create_workflow_dir(vendor_name):
    """Create the workflow directory for a vendor if it doesn't exist."""
    config = get_config()
    project_root = get_project_root()
    base_workflow_dir = str(project_root / config.batch.paths.workflow_dir)
    logger.debug(f"Using workflow_dir: {base_workflow_dir}")
    workflow_dir = os.path.join(base_workflow_dir, vendor_name)
    os.makedirs(workflow_dir, exist_ok=True)
    return workflow_dir


def write_summary_entry(summary_file, vendor, api, spec_path, output_path, status, duration):
    """Write a single summary entry to a CSV file.

    Args:
        summary_file: Path to the summary file
        vendor: Vendor name
        api: API name
        spec_path: Path to the OpenAPI specification
        output_path: Path to the generated workflow
        status: Processing status (success, error, skipped)
        duration: Processing duration in seconds
    """
    try:
        # Determine if we need to write the header
        file_exists = os.path.exists(summary_file) and os.path.getsize(summary_file) > 0
        write_header = not file_exists

        with open(summary_file, "a") as f:
            if write_header:
                f.write("vendor,api,spec_path,output_path,status,duration,timestamp\n")

            # Escape any commas in the paths to avoid CSV issues
            spec_path_escaped = f'"{spec_path}"' if "," in spec_path else spec_path
            output_path_escaped = f'"{output_path}"' if "," in output_path else output_path
            timestamp = datetime.now().isoformat()

            f.write(
                f"{vendor},{api},{spec_path_escaped},{output_path_escaped},{status},{duration:.2f},{timestamp}\n"
            )

        logger.debug(f"Summary entry written to {summary_file}")
        return True
    except Exception as e:
        logger.error(f"Error writing summary entry: {str(e)}")
        return False
