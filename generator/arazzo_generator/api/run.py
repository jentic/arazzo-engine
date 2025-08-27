"""Run script for the Arazzo Generator API.

This script starts the FastAPI server using uvicorn.
"""

import argparse

import uvicorn
from arazzo.arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run the Arazzo Generator API server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    # Start the server
    uvicorn.run(
        "arazzo_generator.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )
