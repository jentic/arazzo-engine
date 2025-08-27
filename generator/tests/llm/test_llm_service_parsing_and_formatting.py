from unittest.mock import patch

from arazzo_generator.llm.litellm_service import LiteLLMService


class TestParsingandFormatting:
    # Tests the parsing of the workflow response
    @patch("arazzo_generator.llm.litellm_service.logger")
    def test_parse_workflow_response(self, mock_logger):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        # Simulate a valid LLM JSON response for workflows
        llm_response = '{"workflows": [{"name": "wf1", "description": "desc1", "operations": []}, {"name": "wf2", "description": "desc2", "operations": []}]}'
        workflows = svc._parse_workflow_response(llm_response)
        assert isinstance(workflows, list)
        assert len(workflows) == 2
        assert workflows[0]["name"] == "wf1"
        assert workflows[1]["name"] == "wf2"
        assert mock_logger.debug.called

    # Tests the parsing of the workflow response when the JSON is malformed
    @patch("arazzo_generator.llm.litellm_service.logger")
    def test_parse_workflow_response_malformed_json(self, mock_logger):
        svc = LiteLLMService(api_key="test-key")

        # Test case 1: Completely invalid JSON syntax
        malformed_response = "not a json at all"
        workflows = svc._parse_workflow_response(malformed_response)
        assert isinstance(workflows, list)
        assert len(workflows) == 0
        mock_logger.error.assert_called()

        # Test case 2: Invalid field types
        malformed_response = (
            '{"workflows": [{"name": 123, "description": true, "operations": "not-an-array"}]}'
        )
        workflows = svc._parse_workflow_response(malformed_response)
        assert isinstance(workflows, list)
        assert len(workflows) == 0

        # Test case 3: Array of non-workflow objects
        malformed_response = "[1, 2, 3]"
        workflows = svc._parse_workflow_response(malformed_response)
        assert isinstance(workflows, list)
        assert len(workflows) == 0

    # Tests the formatting of the user workflow section when there are no user workflows
    def test_format_user_workflow_section_no_user_workflows(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        formatted = svc._format_user_workflow_section(None)
        assert formatted == ""

    # Tests the formatting of the user workflow section when there are user workflows
    def test_format_user_workflow_section_with_user_workflows(self):
        svc = LiteLLMService(api_key="test-key")
        assert svc.api_key == "test-key"
        assert svc.llm_provider == "gemini"

        user_workflow_descriptions = ["desc1", "desc2"]
        formatted = svc._format_user_workflow_section(user_workflow_descriptions)
        assert "desc1" in formatted
        assert "desc2" in formatted
        assert "User-Requested Workflows" in formatted or "Instructions" in formatted
        assert "{formatted_descriptions}" not in formatted

    # Tests the formatting of the user workflow section when the template file is not found
    def test_format_user_workflow_section_file_not_found_error(self, monkeypatch, caplog):
        svc = LiteLLMService(api_key="test-key")
        user_workflow_descriptions = ["desc1", "desc2"]
        formatted_descriptions_list = "- desc1\n- desc2"
        template_content = "HEADER\n{formatted_descriptions}\nFOOTER"

        # Patch open to return our template content
        def fake_open(file, *args, **kwargs):
            class DummyFile:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

                def read(self):
                    return template_content

            return DummyFile()

        monkeypatch.setattr("builtins.open", fake_open)

        result = svc._format_user_workflow_section(user_workflow_descriptions)
        assert "HEADER" in result
        assert "FOOTER" in result
        assert formatted_descriptions_list in result
        assert "{formatted_descriptions}" not in result

        # Now patch open to raise FileNotFoundError and check fallback
        def fake_open_missing(file, *args, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr("builtins.open", fake_open_missing)
        with caplog.at_level("ERROR"):
            result = svc._format_user_workflow_section(user_workflow_descriptions)
        assert result == ""
        assert any(
            "User workflow instructions prompt file not found" in record.message
            for record in caplog.records
        )
