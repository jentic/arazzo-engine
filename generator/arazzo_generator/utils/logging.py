import logging
import logging.config
import logging.handlers
import pathlib
from datetime import datetime

from .config import get_config, get_project_root

# Global variable to store the current session log directory
_current_session_log_dir: pathlib.Path | None = None


def setup_logging(log_level: str = None) -> None:
    """Set up logging configuration using the Pydantic config system.

    Args:
        log_level: Optional log level to override the default from config.
            Must be one of: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
            If None, uses the level from config.
    """
    try:
        config = get_config()
        log_cfg = {
            "level": log_level or config.logging.level,
            "format": config.logging.format,
            "destinations": config.logging.destinations,
            "file": {
                "log_dir": config.logging.file.log_dir,
                "filename": config.logging.file.filename,
            },
            "console": {"use_colors": True},
        }
    except Exception as e:
        logging.warning(
            f"Failed to load Pydantic config: {e}. Ensure that config.toml has not been removed or moved."
        )

    # Create log directory if needed
    if "file" in log_cfg.get("destinations", []):
        log_dir = pathlib.Path(log_cfg["file"]["log_dir"])
        if not log_dir.is_absolute():
            project_root = get_project_root()
            log_dir = project_root / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

    # Set up formatters
    formatters = {"standard": {"format": log_cfg["format"], "datefmt": "%Y-%m-%d %H:%M:%S"}}

    # Set up handlers
    handlers = {}

    # Console handler
    if "console" in log_cfg.get("destinations", []):
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": log_cfg["level"],
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }

    # File handler
    if "file" in log_cfg.get("destinations", []):
        file_cfg = log_cfg["file"]
        log_dir = pathlib.Path(file_cfg["log_dir"])
        if not log_dir.is_absolute():
            project_root = get_project_root()
            log_dir = project_root / log_dir

        # Create base timestamped directory for unified logging
        # This will be shared with LLM logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_log_dir = log_dir / timestamp
        timestamped_log_dir.mkdir(parents=True, exist_ok=True)

        # Store the current session directory for LLM logging to use
        global _current_session_log_dir
        _current_session_log_dir = timestamped_log_dir

        # Use simple filename since directory provides uniqueness
        filename = file_cfg["filename"]

        handlers["file"] = {
            "class": "logging.FileHandler",
            "level": log_cfg["level"],
            "formatter": "standard",
            "filename": str(timestamped_log_dir / filename),
            "mode": "w",  # Write mode - creates new file each time
            "encoding": "utf8",
        }

    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            "": {  # root logger
                "handlers": list(handlers.keys()),
                "level": log_cfg["level"],
                "propagate": True,
            }
        },
    }

    # Apply the configuration
    logging.config.dictConfig(logging_config)


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Name of the logger. If None, returns the root logger.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


# LLM Logging Functions
def setup_log_directory() -> tuple[pathlib.Path, str]:
    """Set up a unified directory for logging both application logs and LLM prompts/responses.

    Returns:
        Tuple containing:
        - Path to the log directory (same as application logs)
        - Timestamp string used for the directory
    """
    logger = get_logger(__name__)

    global _current_session_log_dir

    # If we already have a session directory from application logging, use it
    if _current_session_log_dir is not None:
        logger.debug(f"Using existing session log directory: {_current_session_log_dir}")
        # Extract timestamp from directory name
        timestamp = _current_session_log_dir.name
        return _current_session_log_dir, timestamp

    # Get the log directory from config
    try:
        config = get_config()
        log_dir_name = (
            config.logging.file.log_dir
            if hasattr(config, "logging") and hasattr(config.logging, "file")
            else "logs"
        )
    except Exception as e:
        logger.warning(
            f"Failed to get log directory from config: {e}. Using default 'logs' directory."
        )
        log_dir_name = "logs"

    # Create a new directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_root = get_project_root()
    log_dir = project_root / log_dir_name / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)

    # Store it for future use
    _current_session_log_dir = log_dir

    logger.debug(f"Created new session log directory: {log_dir}")
    return log_dir, timestamp


def log_llm_prompt(
    prompt: str,
    log_dir: pathlib.Path,
    prompt_type: str,
    timestamp: str | None = None,
) -> str:
    """Log the LLM prompt to a file.

    Args:
        prompt: The prompt to log.
        log_dir: Directory to save the log file.
        prompt_type: Type of the prompt (e.g., 'direct_generation', 'endpoint_analysis').
        timestamp: Optional timestamp string. If not provided, current time will be used.

    Returns:
        The timestamp string used for the log.
    """
    logger = get_logger(__name__)

    try:
        # Create prompt file path
        prompt_filename = f"{prompt_type}_prompt.txt"
        prompt_file_path = log_dir / prompt_filename

        # Write the prompt to the log file
        with open(prompt_file_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        logger.debug(f"Logged {prompt_type} prompt to {prompt_file_path}")
        return timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    except Exception as e:
        logger.warning(f"Failed to log prompt: {e}")
        return timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")


def log_llm_response(response: str, log_dir: pathlib.Path, prompt_type: str) -> None:
    """Log the LLM response to a file.

    Args:
        response: The LLM response to log.
        log_dir: Directory to save the log file.
        prompt_type: Type of the prompt (e.g., 'direct_generation', 'endpoint_analysis').
    """
    logger = get_logger(__name__)

    try:
        # Create response file path
        response_filename = f"{prompt_type}_response.txt"
        response_file_path = log_dir / response_filename

        # Write the response to the log file
        with open(response_file_path, "w", encoding="utf-8") as f:
            f.write(response)

        logger.debug(f"Logged {prompt_type} response to {response_file_path}")
    except Exception as e:
        logger.warning(f"Failed to log LLM response: {e}")
