from arazzo_runner.models import ExecutionState, WorkflowExecutionStatus


def test_workflow_execution_status_equality_and_representation():
    """
    Tests that WorkflowExecutionStatus enum members are equal to their string values
    and that their string representations are also their plain string values.
    """
    for status_member in WorkflowExecutionStatus:
        # Test direct equality with its string value (due to inheriting str)
        assert status_member == status_member.value

        # Test str() representation
        assert str(status_member) == status_member.value

        # Test repr() representation (since __repr__ is defined as self.value)
        assert repr(status_member) == status_member.value


class TestExecutionStateGotoStepId:
    """Tests for the goto_step_id field on ExecutionState."""

    def test_goto_step_id_field_exists(self):
        """Test that ExecutionState has the goto_step_id field."""
        state = ExecutionState(workflow_id="test")
        assert hasattr(state, "goto_step_id")
        assert state.goto_step_id is None

    def test_goto_step_id_can_be_set(self):
        """Test that goto_step_id can be set."""
        state = ExecutionState(workflow_id="test")
        state.goto_step_id = "target-step"
        assert state.goto_step_id == "target-step"

    def test_goto_step_id_can_be_cleared(self):
        """Test that goto_step_id can be cleared."""
        state = ExecutionState(workflow_id="test")
        state.goto_step_id = "target-step"
        state.goto_step_id = None
        assert state.goto_step_id is None
