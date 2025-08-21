#!/usr/bin/env python3
"""Main entry point for the OpenAPI to Arazzo generator."""

import sys

from arazzo_generator.utils.logging import get_logger

from .main import cli

# Initialize logger
logger = get_logger(__name__)


def main():
    """Entry point for PDM scripts."""
    try:
        logger.info("Starting CLI application")
        sys.exit(cli())
    except Exception as _:
        logger.critical("CLI execution failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
