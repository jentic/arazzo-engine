#!/usr/bin/env python3
"""
Integration tests for ArazzoRunner workflows that span multiple API sources.

Exercises complete workflow execution with two distinct OpenAPI sources,
including cross-source output chaining (an output from a petstore step used
as a parameter in a users step).

OperationFinder unit tests for multi-source routing live in
test_operation_finder.py (TestOperationFinderWithTwoSources).
"""

import os
import unittest

import yaml

from tests.mocks import MockHTTPExecutor

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "test_data")


def _yaml(rel: str) -> dict:
    with open(os.path.join(_FIXTURES_DIR, rel)) as f:
        return yaml.safe_load(f)


PETSTORE_SPEC = _yaml("petstore/petstore.openapi.yaml")
PETSTORE_SOURCE_DESCRIPTIONS = {"petstore": PETSTORE_SPEC}

_USERS_SPEC = _yaml("mock_apis/users.openapi.yaml")
MULTI_SOURCE_DESCRIPTIONS = {"petstore": PETSTORE_SPEC, "users": _USERS_SPEC}

SINGLE_SOURCE_ARAZZO_DOC = _yaml("petstore/single_source.arazzo.yaml")
TWO_SOURCE_ARAZZO_DOC = _yaml("cross_source/cross_source.arazzo.yaml")


class TestArazzoWorkflowWithTwoSources(unittest.TestCase):
    """
    End-to-end tests using ArazzoRunner with MockHTTPExecutor.
    Verifies that the runner correctly routes steps to their respective
    source API and that cross-source output chaining works.
    """

    def _make_runner(self, arazzo_doc: dict, source_descriptions: dict):
        """Return a configured ArazzoRunner backed by MockHTTPExecutor."""
        from arazzo_runner import ArazzoRunner

        http_client = MockHTTPExecutor()

        # petstore responses — register specific before general so the
        # more-specific /pets/42 route is matched before the /pets catch-all.
        http_client.add_static_response(
            method="GET",
            url_pattern="/pets/42",
            status_code=200,
            json_data={"id": 42, "name": "Fido", "tag": "dog"},
        )
        http_client.add_static_response(
            method="GET",
            url_pattern="/pets",
            status_code=200,
            json_data=[{"id": 42, "name": "Fido"}, {"id": 7, "name": "Whiskers"}],
        )

        # users service response
        http_client.add_static_response(
            method="GET",
            url_pattern="/users/42",
            status_code=200,
            json_data={"id": 42, "username": "fido_owner"},
        )

        runner = ArazzoRunner(
            arazzo_doc=arazzo_doc,
            source_descriptions=source_descriptions,
            http_client=http_client,
        )
        return runner, http_client

    # --- single-source baseline (mirrors demo.py) ---

    def test_single_source_workflow_completes(self):
        """
        Baseline: a petstore-only two-step workflow completes with the
        expected outputs, confirming the ~1 decode fix does not break the
        standard single-source path.
        """
        from arazzo_runner import WorkflowExecutionStatus

        runner, _ = self._make_runner(SINGLE_SOURCE_ARAZZO_DOC, PETSTORE_SOURCE_DESCRIPTIONS)
        result = runner.execute_workflow("listThenFetchPet")

        self.assertEqual(result.status, WorkflowExecutionStatus.WORKFLOW_COMPLETE)
        self.assertEqual(result.outputs.get("petName"), "Fido")
        self.assertEqual(result.outputs.get("petTag"), "dog")

    def test_single_source_workflow_makes_two_http_calls(self):
        """Two steps → exactly two HTTP requests to the petstore base URL."""
        runner, http_client = self._make_runner(
            SINGLE_SOURCE_ARAZZO_DOC, PETSTORE_SOURCE_DESCRIPTIONS
        )
        runner.execute_workflow("listThenFetchPet")

        self.assertEqual(http_client.get_request_count(), 2)
        methods = [r["method"].upper() for r in http_client.requests]
        self.assertEqual(methods, ["GET", "GET"])

    # --- two-source workflow ---

    def test_two_source_workflow_completes(self):
        """
        A three-step workflow that calls petstore (twice) then users
        should complete successfully with outputs from both APIs.
        """
        from arazzo_runner import WorkflowExecutionStatus

        runner, _ = self._make_runner(TWO_SOURCE_ARAZZO_DOC, MULTI_SOURCE_DESCRIPTIONS)
        result = runner.execute_workflow("crossSourceWorkflow")

        self.assertEqual(result.status, WorkflowExecutionStatus.WORKFLOW_COMPLETE)
        self.assertEqual(result.outputs.get("petName"), "Fido")
        self.assertEqual(result.outputs.get("username"), "fido_owner")

    def test_two_source_workflow_makes_three_http_calls(self):
        """Three steps → exactly three HTTP requests total."""
        runner, http_client = self._make_runner(TWO_SOURCE_ARAZZO_DOC, MULTI_SOURCE_DESCRIPTIONS)
        runner.execute_workflow("crossSourceWorkflow")

        self.assertEqual(http_client.get_request_count(), 3)

    def test_two_source_workflow_calls_both_base_urls(self):
        """
        Requests must hit both petstore.example.com and users.example.com,
        confirming the runner routes to the correct source for each step.
        """
        runner, http_client = self._make_runner(TWO_SOURCE_ARAZZO_DOC, MULTI_SOURCE_DESCRIPTIONS)
        runner.execute_workflow("crossSourceWorkflow")

        urls = [r["url"] for r in http_client.requests]
        self.assertTrue(any("petstore.example.com" in u for u in urls),
                        f"No petstore URL among: {urls}")
        self.assertTrue(any("users.example.com" in u for u in urls),
                        f"No users URL among: {urls}")

    def test_cross_source_output_chaining(self):
        """
        The firstPetId output from the petstore step (42) is forwarded as
        userId to the users step, producing the expected username.
        """
        from arazzo_runner import WorkflowExecutionStatus

        runner, http_client = self._make_runner(TWO_SOURCE_ARAZZO_DOC, MULTI_SOURCE_DESCRIPTIONS)
        result = runner.execute_workflow("crossSourceWorkflow")

        self.assertEqual(result.status, WorkflowExecutionStatus.WORKFLOW_COMPLETE)

        # Confirm the users request was made with the ID chained from the petstore step
        users_requests = [r for r in http_client.requests if "users.example.com" in r["url"]]
        self.assertEqual(len(users_requests), 1)
        self.assertIn("42", users_requests[0]["url"])

    def test_step_outputs_available_for_each_source(self):
        """
        Step-level outputs from both sources are present on the result so
        downstream steps (and callers) can inspect them.
        """
        runner, _ = self._make_runner(TWO_SOURCE_ARAZZO_DOC, MULTI_SOURCE_DESCRIPTIONS)
        result = runner.execute_workflow("crossSourceWorkflow")

        self.assertIsNotNone(result.step_outputs)
        self.assertIn("listPetsStep", result.step_outputs)
        self.assertIn("getPetStep",   result.step_outputs)
        self.assertIn("getUserStep",  result.step_outputs)


# ---------------------------------------------------------------------------
# Workflow using operationId instead of operationPath
# ---------------------------------------------------------------------------

# Steps reference operations by operationId rather than operationPath.
# Confirms the operationId dispatch path (OperationFinder.find_by_id) continues
# to work correctly alongside the operationPath fix.
_OPERATION_ID_ARAZZO_DOC = _yaml("petstore/operation_id.arazzo.yaml")


class TestArazzoWorkflowWithOperationId(unittest.TestCase):
    """
    End-to-end tests confirming that steps using operationId (rather than
    operationPath) still execute correctly.  This exercises
    OperationFinder.find_by_id and StepExecutor._execute_operation_by_id
    through the full ArazzoRunner pipeline.
    """

    def _make_runner(self):
        http_client = MockHTTPExecutor()
        # Register specific path before general so /pets/42 wins over /pets
        http_client.add_static_response(
            method="GET",
            url_pattern="/pets/42",
            status_code=200,
            json_data={"id": 42, "name": "Fido", "tag": "dog"},
        )
        http_client.add_static_response(
            method="GET",
            url_pattern="/pets",
            status_code=200,
            json_data=[{"id": 42, "name": "Fido"}, {"id": 7, "name": "Whiskers"}],
        )
        from arazzo_runner import ArazzoRunner
        runner = ArazzoRunner(
            arazzo_doc=_OPERATION_ID_ARAZZO_DOC,
            source_descriptions=PETSTORE_SOURCE_DESCRIPTIONS,
            http_client=http_client,
        )
        return runner, http_client

    def test_workflow_completes(self):
        """A two-step operationId workflow reaches WORKFLOW_COMPLETE status."""
        from arazzo_runner import WorkflowExecutionStatus
        runner, _ = self._make_runner()
        result = runner.execute_workflow("operationIdWorkflow")
        self.assertEqual(result.status, WorkflowExecutionStatus.WORKFLOW_COMPLETE)

    def test_workflow_outputs(self):
        """Outputs chained across operationId steps contain the expected values."""
        runner, _ = self._make_runner()
        result = runner.execute_workflow("operationIdWorkflow")
        self.assertEqual(result.outputs.get("petName"), "Fido")
        self.assertEqual(result.outputs.get("petTag"), "dog")

    def test_workflow_makes_two_http_calls(self):
        """Two steps → exactly two HTTP requests."""
        runner, http_client = self._make_runner()
        runner.execute_workflow("operationIdWorkflow")
        self.assertEqual(http_client.get_request_count(), 2)

    def test_step_outputs_are_populated(self):
        """Both step outputs are recorded on the result."""
        runner, _ = self._make_runner()
        result = runner.execute_workflow("operationIdWorkflow")
        self.assertIn("listPetsStep", result.step_outputs)
        self.assertIn("getPetStep", result.step_outputs)


if __name__ == "__main__":
    unittest.main()
