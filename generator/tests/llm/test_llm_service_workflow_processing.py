import json
from unittest.mock import patch

from arazzo_generator.llm.litellm_service import LiteLLMService


class TestLLMServiceWorkflowProcessing:
    # Tests the test_process_workflows function when workflows contain all required fields i.e. should stay the same
    def test_process_workflows_no_missing_fields(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        workflows = [
            {
                "workflowId": "wf1",
                "rank": 5,
                "operations": [{"name": "op1", "description": "desc1"}],
            },
            {
                "workflowId": "wf2",
                "rank": 5,
                "operations": [{"name": "op2", "description": "desc2"}],
            },
        ]
        processed = svc._process_workflows(workflows)
        # wf1 should retain all properties
        assert processed[0]["workflowId"] == "wf1"
        assert processed[0]["rank"] == 5
        assert processed[0]["operations"][0]["description"] == "desc1"
        # wf2 should retain all properties
        assert processed[1]["workflowId"] == "wf2"
        assert processed[1]["rank"] == 5
        assert processed[1]["operations"][0]["description"] == "desc2"

    # Tests the test_process_workflows function when workflows are missing required fields i.e. should be added
    def test_process_workflows_adds_missing_fields(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        workflows = [
            {"name": "wf1", "operations": [{"name": "op1"}]},
            {
                "workflowId": "wf2",
                "operations": [{"name": "op2", "description": "desc2"}],
            },
        ]
        processed = svc._process_workflows(workflows)
        # wf1 should have workflowId, rank, and operation description added
        assert processed[0]["workflowId"] == "wf1"
        assert processed[0]["rank"] == 5
        assert processed[0]["operations"][0]["description"].startswith("Performs the op1")
        # wf2 should retain its workflowId and operation description
        assert processed[1]["workflowId"] == "wf2"
        assert processed[1]["operations"][0]["description"] == "desc2"

    # Tests the test_recover_workflows_from_malformed_json function when workflows contain malformed JSON
    def test_recover_workflows_from_malformed_json_brackets(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        # Missing opening bracket
        malformed = '{"name": "wf1", "operations": []}]'
        recovered = svc._recover_workflows_from_malformed_json(malformed)
        assert isinstance(recovered, list)
        # Should try to parse and return at least one dict if possible
        if recovered:
            assert isinstance(recovered[0], dict)

    # Tests the test_recover_workflows_from_malformed_json function when a JSONDecodeError is raised
    @patch("json.loads", side_effect=json.JSONDecodeError("Expecting value", "doc", 0))
    def test_recover_workflows_from_malformed_json_error(self, mock_json_loads):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        # Simulate an LLM output cut-off, so JSON recovery fails
        malformed = '{"name": "wf1", "operations": []}]'
        recovered = svc._recover_workflows_from_malformed_json(malformed)
        # Should handle the error gracefully and return an empty list
        assert isinstance(recovered, list)
        assert recovered == []

    # Tests the test_recover_workflows_from_malformed_json function when an llm token limit is reached (cut off JSON)
    def test_recover_workflows_from_malformed_json_token_limit(self):
        svc = LiteLLMService(api_key="test-key")

        # Simulate LLM response cut off mid-workflow due to token limit
        truncated_response = """[
            {
                "name": "Workflow1",
                "description": "Complete workflow",
                "type": "process",
                "operations": [],
                "rank": 5
            },
            {
                "name": "Workflow2",
                "description": "Incomplete workflow due to max tokens",
                "operations": [
                    {
                        "name": "Operation1",
                        "endpoint": "/pets",
                        "method": "GET",
                        "description": "This operation..."""

        recovered = svc._recover_workflows_from_malformed_json(truncated_response)

        # Should only recover the complete workflow
        assert isinstance(recovered, list)
        assert len(recovered) == 1  # Only Workflow1 should be recovered

        # Verify complete workflow was recovered correctly
        workflow = recovered[0]
        assert workflow["name"] == "Workflow1"
        assert workflow["description"] == "Complete workflow"
        assert workflow["type"] == "process"
        assert workflow["operations"] == []
        assert workflow["rank"] == 5

        # Verify incomplete workflow was not included
        assert not any(w["name"] == "Workflow2" for w in recovered)
