"""
Pydantic-based configuration management for the Jentic Arazzo Generator.

This module provides a centralized configuration system that loads settings from
config.toml using Pydantic models for validation and type safety.
"""

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoggingFileConfig(BaseModel):
    """File logging configuration."""

    log_dir: str = Field(default="logs", description="Directory for log files")
    filename: str = Field(default="jentic.log", description="Log filename")


class LoggingPathsConfig(BaseModel):
    """Logging paths configuration."""

    logs_dir: str = Field(default="logs", description="Main logs directory")
    batch_logs_dir: str = Field(default="batch_logs", description="Batch processing logs directory")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    destinations: list[Literal["console", "file"]] = Field(
        default=["console", "file"], description="Output destinations for logs"
    )
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )
    file: LoggingFileConfig = Field(default_factory=LoggingFileConfig)
    paths: LoggingPathsConfig = Field(default_factory=LoggingPathsConfig)


class AppConfig(BaseModel):
    """Application configuration."""

    environment: Literal["development", "production", "testing"] = Field(
        default="development", description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")


class BatchPathsConfig(BaseModel):
    """Batch processing paths configuration."""

    openapi_dir: str = Field(
        default="examples/openapi_specs",
        description="Directory containing OpenAPI specifications",
    )
    workflow_dir: str = Field(
        default="examples/workflows", description="Directory for generated workflows"
    )


class BatchConfig(BaseModel):
    """Batch processing configuration."""

    paths: BatchPathsConfig = Field(default_factory=BatchPathsConfig)


class LLMConfig(BaseModel):
    """LLM configuration."""

    llm_provider: str = Field(
        default="gemini",
        description="Default LLM provider to use (e.g., 'gemini', 'openai', 'anthropic')",
    )
    llm_model: str = Field(
        default="gemini/gemini-2.5-flash-preview-05-20",
        description="Default LLM model to use",
    )


class Config(BaseModel):
    """Main configuration model."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    batch: BatchConfig = Field(default_factory=BatchConfig)

    @field_validator("logging", mode="before")
    @classmethod
    def validate_logging_config(cls, v):
        """Ensure logging configuration is properly structured."""
        if isinstance(v, dict):
            # Handle nested file and paths configurations
            if "file" in v and isinstance(v["file"], dict):
                v["file"] = LoggingFileConfig(**v["file"])
            if "paths" in v and isinstance(v["paths"], dict):
                v["paths"] = LoggingPathsConfig(**v["paths"])
        return v

    @field_validator("batch", mode="before")
    @classmethod
    def validate_batch_config(cls, v):
        """Ensure batch configuration is properly structured."""
        if isinstance(v, dict):
            # Handle nested paths configuration
            if "paths" in v and isinstance(v["paths"], dict):
                v["paths"] = BatchPathsConfig(**v["paths"])
        return v

    @field_validator("llm", mode="before")
    @classmethod
    def validate_llm_config(cls, v):
        """Ensure LLM configuration is properly structured."""
        if isinstance(v, dict):
            return LLMConfig(**v)
        return v


def get_project_root() -> Path:
    """
    Get the project root directory by finding the directory containing config.toml.

    Returns:
        Path: The project root directory
    """
    # Start from current file and walk up to find config.toml
    current_path = Path(__file__).resolve()

    for parent in [current_path] + list(current_path.parents):
        if (parent / "config.toml").exists():
            return parent

    # Fallback to current working directory
    return Path.cwd()


@lru_cache(maxsize=1)
def load_config() -> Config:
    """
    Load configuration from config.toml file.

    Returns:
        Config: Parsed and validated configuration object

    Raises:
        FileNotFoundError: If config.toml is not found
        tomllib.TOMLDecodeError: If config.toml is malformed
        pydantic.ValidationError: If configuration values are invalid
    """
    project_root = get_project_root()
    config_path = project_root / "config.toml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise tomllib.TOMLDecodeError(f"Invalid TOML in {config_path}: {e}") from e

    return Config(**config_data)


def get_config() -> Config:
    """
    Get the cached configuration instance.

    Returns:
        Config: The configuration object
    """
    return load_config()


def get_output_path(output_dir: str | None = None) -> Path:
    """
    Get the output path for generated files.

    Args:
        output_dir: Optional custom output directory

    Returns:
        Path: The output directory path
    """
    if output_dir:
        return Path(output_dir)

    # Use config directly
    config = get_config()
    project_root = get_project_root()
    return project_root / config.batch.paths.workflow_dir
