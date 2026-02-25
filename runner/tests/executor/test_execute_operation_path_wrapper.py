#!/usr/bin/env python3
"""
Tests for StepExecutor.execute_operation with the "METHOD /path" convenience format.

This covers the pipeline:
  operation_path string → split on space → find_by_http_path_and_method → HTTP request

This is a separate lookup path from the JSON Pointer / operationPath mechanism
tested in test_operation_finder.py.
"""

import os
import unittest
from unittest.mock import MagicMock

import yaml

from arazzo_runner.executor.step_executor import StepExecutor
from arazzo_runner.http import HTTPExecutor

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "test_data")

PETSTORE_SOURCE_DESCRIPTIONS = {
    "petstore": yaml.safe_load(
        open(os.path.join(_FIXTURES_DIR, "petstore/petstore.openapi.yaml"))
    )
}


class TestExecuteOperationPathWrapper(unittest.TestCase):
    """
    Tests for StepExecutor.execute_operation with operation_path="METHOD /path".

    This exercises the full path: string split → find_by_http_path_and_method →
    HTTP request.  Our ~1 decode fix must not have introduced any regression in
    this entirely separate lookup code path.
    """

    def _make_executor(self):
        mock_http = MagicMock(spec=HTTPExecutor)
        mock_http.execute_request.return_value = {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"id": 42, "name": "Fido", "tag": "dog"},
        }
        executor = StepExecutor(
            http_client=mock_http,
            source_descriptions=PETSTORE_SOURCE_DESCRIPTIONS,
            testing_mode=True,
        )
        return executor, mock_http

    def test_get_simple_path(self):
        """execute_operation('GET /pets') resolves and fires the HTTP request."""
        executor, mock_http = self._make_executor()
        executor.execute_operation(
            inputs={},
            operation_path="GET /pets",
        )
        mock_http.execute_request.assert_called_once()
        call_kwargs = mock_http.execute_request.call_args[1]
        self.assertEqual(call_kwargs["method"], "get")
        self.assertIn("/pets", call_kwargs["url"])

    def test_get_parameterised_path(self):
        """execute_operation('GET /pets/{petId}') resolves and fires with the correct URL template."""
        executor, mock_http = self._make_executor()
        executor.execute_operation(
            inputs={"petId": "42"},
            operation_path="GET /pets/{petId}",
        )
        mock_http.execute_request.assert_called_once()
        call_kwargs = mock_http.execute_request.call_args[1]
        self.assertEqual(call_kwargs["method"], "get")
        self.assertIn("/pets/{petId}", call_kwargs["url"])

    def test_invalid_format_raises(self):
        """A path string with no space separator raises ValueError."""
        executor, _ = self._make_executor()
        with self.assertRaises(ValueError):
            executor.execute_operation(inputs={}, operation_path="GET/pets")

    def test_unknown_operation_raises(self):
        """An operation_path that matches no spec entry raises ValueError."""
        executor, _ = self._make_executor()
        with self.assertRaises(ValueError):
            executor.execute_operation(inputs={}, operation_path="GET /nonexistent")


if __name__ == "__main__":
    unittest.main()
