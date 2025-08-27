"""Tests for the logging module."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import arazzo_generator.utils.logging as logging_module
from arazzo_generator.utils.logging import (
    get_logger,
    log_llm_prompt,
    log_llm_response,
    setup_log_directory,
    setup_logging,
)


# Fixtures
@pytest.fixture
def mock_config(monkeypatch):
    """Fixture to provide a mock config object."""

    class MockLoggingConfig:
        level = "INFO"
        format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        destinations = []

        class FileConfig:
            log_dir = "logs"
            filename = "app.log"

        file = FileConfig()

    class MockConfig:
        logging = MockLoggingConfig()

    # Patch the get_config function to return our mock config
    def mock_get_config():
        return MockConfig()

    monkeypatch.setattr("arazzo_generator.utils.logging.get_config", mock_get_config)
    return MockConfig


@pytest.fixture
def mock_datetime():
    """Fixture to mock datetime for consistent timestamps."""
    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "20250101_120000"
        yield mock_dt


@pytest.fixture
def mock_get_project_root():
    """Fixture to mock get_project_root."""
    with patch("arazzo_generator.utils.logging.get_project_root") as mock_root:
        mock_root.return_value = Path("/project")
        yield mock_root


@pytest.fixture
def mock_mkdir():
    """Fixture to mock Path.mkdir."""
    with patch("pathlib.Path.mkdir") as mock:
        yield mock


class TestLogging:
    def setup_method(self):
        """Reset logging configuration before each test."""
        # Remove all handlers from root logger
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

        # Reset the global session directory
        global _current_session_log_dir
        _current_session_log_dir = None

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_setup_logging_console_only(self, mock_config):
        """Test setting up logging with console output only."""
        mock_config.logging.destinations = ["console"]

        with patch("logging.config.dictConfig") as mock_dict_config:
            # Reset any existing logging configuration
            logging.root.handlers = []
            logging.root.setLevel(logging.NOTSET)

            setup_logging()

        # Verify dictConfig was called with expected config
        args, kwargs = mock_dict_config.call_args
        config = args[0]

        assert "console" in config["handlers"]
        assert "file" not in config["handlers"]
        assert config["loggers"][""]["handlers"] == ["console"]

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_absolute", return_value=False)
    @patch("arazzo_generator.utils.logging.get_project_root", return_value=Path("/project"))
    @patch("arazzo_generator.utils.logging.datetime")
    def test_setup_logging_with_file(
        self,
        mock_datetime,
        mock_get_project_root,
        mock_is_absolute,
        mock_mkdir,
        mock_config,
    ):
        """Test setting up logging with file output."""
        mock_config.logging.destinations = ["file"]
        mock_config.logging.file.log_dir = "test_logs"
        mock_config.logging.file.filename = "app.log"

        # Setup datetime mock
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20250101_120000"
        mock_datetime.now.return_value = mock_now

        with patch("logging.config.dictConfig") as mock_dict_config:
            # Reset any existing logging configuration
            logging.root.handlers = []
            logging.root.setLevel(logging.NOTSET)

            setup_logging()

        # Verify directory was created (once for the base dir, once for timestamped dir)
        assert mock_mkdir.call_count == 2
        assert mock_mkdir.call_args_list[0][1] == {"parents": True, "exist_ok": True}
        assert mock_mkdir.call_args_list[1][1] == {"parents": True, "exist_ok": True}

        # Verify dictConfig was called with file handler
        args, _ = mock_dict_config.call_args
        config = args[0]

        assert "file" in config["handlers"]
        # The path should use the test_logs directory from our mock config
        assert (
            config["handlers"]["file"]["filename"] == "/project/test_logs/20250101_120000/app.log"
        )

    @patch("pathlib.Path.mkdir")
    @patch("arazzo_generator.utils.logging.get_project_root")
    @patch("arazzo_generator.utils.logging.datetime")
    @patch("arazzo_generator.utils.logging.get_config")
    def test_setup_log_directory_new_session(
        self, mock_get_config, mock_datetime, mock_get_project_root, mock_mkdir
    ):
        """Test setting up a new log directory."""

        original_dir = logging_module._current_session_log_dir
        logging_module._current_session_log_dir = None

        try:
            # Setup mocks
            mock_get_project_root.return_value = Path("/project")
            mock_now = MagicMock()
            mock_now.strftime.return_value = "20250101_120000"
            mock_datetime.now.return_value = mock_now

            # Mock the config to return our test log dir
            mock_config = MagicMock()
            mock_config.logging = MagicMock()
            mock_config.logging.file = MagicMock()
            mock_config.logging.file.log_dir = "test_logs"
            mock_get_config.return_value = mock_config

            # Call the function
            log_dir, timestamp = setup_log_directory()

            # Verify the results
            assert timestamp == "20250101_120000"
            assert str(log_dir) == "/project/test_logs/20250101_120000"

            # Verify the global variable was set
            assert logging_module._current_session_log_dir == Path(
                "/project/test_logs/20250101_120000"
            )

            # Verify mkdir was called with the correct arguments
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

            # Verify the directory path is correct
            # The actual call might have a different representation, so we'll just check the mkdir was called

        finally:
            # Restore the original global variable
            logging_module._current_session_log_dir = original_dir

    @patch("pathlib.Path.mkdir")
    @patch("arazzo_generator.utils.logging.datetime")
    @patch("arazzo_generator.utils.logging.get_project_root", return_value=Path("/project"))
    def test_setup_log_directory_existing_session(
        self, mock_get_project_root, mock_datetime, mock_mkdir
    ):
        """Test that setup_log_directory reuses existing session directory."""
        # Reset the global variable in the module

        original_dir = logging_module._current_session_log_dir
        logging_module._current_session_log_dir = Path("/project/test_logs/20250101_120000")

        try:
            # Setup mock
            mock_now = MagicMock()
            mock_now.strftime.return_value = (
                "20250101_120000"  # Should match the timestamp in the path above
            )
            mock_datetime.now.return_value = mock_now

            # Call the function
            log_dir, timestamp = setup_log_directory()

            # Verify the results
            assert timestamp == "20250101_120000"
            assert str(log_dir) == "/project/test_logs/20250101_120000"

            # Should not create any new directories since we're reusing the existing one
            mock_mkdir.assert_not_called()

        finally:
            # Restore the original global variable
            logging_module._current_session_log_dir = original_dir

    def test_log_llm_prompt(self, tmp_path, prompt="example prompt", log_type="test_generation"):
        """Test logging an LLM prompt to a file."""
        with (
            patch("builtins.open", create=True) as mock_open,
            patch("time.time", return_value=1234567890.123456),
        ):
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            timestamp = log_llm_prompt(prompt, tmp_path, log_type)

            # Verify file was opened with correct path
            expected_path = tmp_path / f"{log_type}_prompt.txt"
            mock_open.assert_called_once_with(expected_path, "w", encoding="utf-8")

            # Verify content was written
            mock_file.write.assert_called_once_with(prompt)

            # Verify timestamp was returned and formatted correctly
            assert timestamp is not None
            assert isinstance(timestamp, str)
            assert timestamp  # Not empty

    def test_log_llm_response(self, tmp_path, log_type="test_generation"):
        """Test logging an LLM response to a file."""
        test_response = "This is a test response."

        with (
            patch("builtins.open", create=True) as mock_open,
            patch("time.time", return_value=1234567890.123456),
        ):
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            log_llm_response(test_response, tmp_path, log_type)

            # Verify file was opened with correct path
            expected_path = tmp_path / f"{log_type}_response.txt"
            mock_open.assert_called_once_with(expected_path, "w", encoding="utf-8")

            # Verify content was written
            mock_file.write.assert_called_once_with(test_response)

            # Verify no return value (function returns None)
            assert log_llm_response(test_response, tmp_path, log_type) is None
