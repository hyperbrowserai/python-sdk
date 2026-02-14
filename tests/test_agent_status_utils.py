from hyperbrowser.client.managers.agent_status_utils import (
    AGENT_TERMINAL_STATUSES,
    is_agent_terminal_status,
)


def test_agent_terminal_statuses_constant_contains_expected_values():
    assert AGENT_TERMINAL_STATUSES == {"completed", "failed", "stopped"}


def test_is_agent_terminal_status_returns_true_for_terminal_values():
    assert is_agent_terminal_status("completed") is True
    assert is_agent_terminal_status("failed") is True
    assert is_agent_terminal_status("stopped") is True


def test_is_agent_terminal_status_returns_false_for_non_terminal_values():
    assert is_agent_terminal_status("running") is False
    assert is_agent_terminal_status("pending") is False
