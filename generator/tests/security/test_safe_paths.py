"""Tests for the safe_paths module."""

import os
import pathlib
import tempfile
from unittest import mock

import pytest

from arazzo_generator.security import safe_paths


@pytest.fixture(autouse=True)
def reset_safe_roots():
    """Fixture to reset SAFE_ROOTS to its initial state before each test."""
    original_roots = list(safe_paths.SAFE_ROOTS)
    yield
    safe_paths.SAFE_ROOTS = original_roots


def test_project_root_is_safe():
    """Test that a path within the project root is considered safe."""
    assert safe_paths.is_within_safe_roots(safe_paths.PROJECT_ROOT / "README.md")


def test_external_directory_is_safe():
    """Test that a path within a configured external directory is safe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        external_path = pathlib.Path(tmpdir)
        (external_path / "test.json").touch()

        with mock.patch.dict(os.environ, {"OPENAPI_SPECS_DIR": str(external_path)}):
            safe_paths.add_external_root()
            assert safe_paths.is_within_safe_roots(external_path / "test.json")


def test_unsafe_directory_is_not_safe():
    """Test that a path outside of any safe root is not considered safe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        unsafe_path = pathlib.Path(tmpdir) / "unsafe.json"
        unsafe_path.touch()
        assert not safe_paths.is_within_safe_roots(unsafe_path)


def test_parent_directory_traversal_is_not_safe():
    """Test that a path attempting directory traversal is not safe."""
    # This path will resolve outside the project root.
    unsafe_path = safe_paths.PROJECT_ROOT / ".." / "some_other_file.txt"
    assert not safe_paths.is_within_safe_roots(unsafe_path)


@pytest.mark.parametrize(
    "root_path_str",
    [
        "/",  # Unix root
        "C:\\",  # Windows root
    ],
)
def test_filesystem_roots_are_not_allowed(capsys, root_path_str):
    """Test that setting various filesystem roots as the external directory is rejected."""
    root_dir = pathlib.Path(root_path_str)
    with mock.patch.dict(os.environ, {"OPENAPI_SPECS_DIR": str(root_dir)}):
        safe_paths.add_external_root()
        captured = capsys.readouterr()
        assert "Warning: Invalid OPENAPI_SPECS_DIR" in captured.out
        assert root_dir not in safe_paths.SAFE_ROOTS


def test_non_existent_external_dir_is_ignored(capsys):
    """Test that a non-existent external directory is safely ignored."""
    non_existent_path = "/path/that/does/not/exist"
    with mock.patch.dict(os.environ, {"OPENAPI_SPECS_DIR": non_existent_path}):
        safe_paths.add_external_root()
        captured = capsys.readouterr()
        assert "Warning: Invalid OPENAPI_SPECS_DIR" in captured.out
