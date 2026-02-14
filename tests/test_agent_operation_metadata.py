from hyperbrowser.client.managers.agent_operation_metadata import (
    BROWSER_USE_OPERATION_METADATA,
    CLAUDE_COMPUTER_USE_OPERATION_METADATA,
    CUA_OPERATION_METADATA,
    GEMINI_COMPUTER_USE_OPERATION_METADATA,
    HYPER_AGENT_OPERATION_METADATA,
)


def test_browser_use_operation_metadata_values():
    assert (
        BROWSER_USE_OPERATION_METADATA.start_payload_error_message
        == "Failed to serialize browser-use start params"
    )
    assert BROWSER_USE_OPERATION_METADATA.start_operation_name == "browser-use start"
    assert BROWSER_USE_OPERATION_METADATA.task_operation_name == "browser-use task"
    assert (
        BROWSER_USE_OPERATION_METADATA.status_operation_name
        == "browser-use task status"
    )
    assert BROWSER_USE_OPERATION_METADATA.stop_operation_name == "browser-use task stop"
    assert (
        BROWSER_USE_OPERATION_METADATA.start_error_message
        == "Failed to start browser-use task job"
    )
    assert (
        BROWSER_USE_OPERATION_METADATA.operation_name_prefix == "browser-use task job "
    )


def test_hyper_agent_operation_metadata_values():
    assert (
        HYPER_AGENT_OPERATION_METADATA.start_payload_error_message
        == "Failed to serialize HyperAgent start params"
    )
    assert HYPER_AGENT_OPERATION_METADATA.start_operation_name == "hyper agent start"
    assert HYPER_AGENT_OPERATION_METADATA.task_operation_name == "hyper agent task"
    assert (
        HYPER_AGENT_OPERATION_METADATA.status_operation_name
        == "hyper agent task status"
    )
    assert HYPER_AGENT_OPERATION_METADATA.stop_operation_name == "hyper agent task stop"
    assert (
        HYPER_AGENT_OPERATION_METADATA.start_error_message
        == "Failed to start HyperAgent task"
    )
    assert HYPER_AGENT_OPERATION_METADATA.operation_name_prefix == "HyperAgent task "


def test_gemini_operation_metadata_values():
    assert (
        GEMINI_COMPUTER_USE_OPERATION_METADATA.start_payload_error_message
        == "Failed to serialize Gemini Computer Use start params"
    )
    assert (
        GEMINI_COMPUTER_USE_OPERATION_METADATA.start_operation_name
        == "gemini computer use start"
    )
    assert (
        GEMINI_COMPUTER_USE_OPERATION_METADATA.task_operation_name
        == "gemini computer use task"
    )
    assert (
        GEMINI_COMPUTER_USE_OPERATION_METADATA.status_operation_name
        == "gemini computer use task status"
    )
    assert (
        GEMINI_COMPUTER_USE_OPERATION_METADATA.stop_operation_name
        == "gemini computer use task stop"
    )
    assert (
        GEMINI_COMPUTER_USE_OPERATION_METADATA.start_error_message
        == "Failed to start Gemini Computer Use task job"
    )
    assert (
        GEMINI_COMPUTER_USE_OPERATION_METADATA.operation_name_prefix
        == "Gemini Computer Use task job "
    )


def test_claude_operation_metadata_values():
    assert (
        CLAUDE_COMPUTER_USE_OPERATION_METADATA.start_payload_error_message
        == "Failed to serialize Claude Computer Use start params"
    )
    assert (
        CLAUDE_COMPUTER_USE_OPERATION_METADATA.start_operation_name
        == "claude computer use start"
    )
    assert (
        CLAUDE_COMPUTER_USE_OPERATION_METADATA.task_operation_name
        == "claude computer use task"
    )
    assert (
        CLAUDE_COMPUTER_USE_OPERATION_METADATA.status_operation_name
        == "claude computer use task status"
    )
    assert (
        CLAUDE_COMPUTER_USE_OPERATION_METADATA.stop_operation_name
        == "claude computer use task stop"
    )
    assert (
        CLAUDE_COMPUTER_USE_OPERATION_METADATA.start_error_message
        == "Failed to start Claude Computer Use task job"
    )
    assert (
        CLAUDE_COMPUTER_USE_OPERATION_METADATA.operation_name_prefix
        == "Claude Computer Use task job "
    )


def test_cua_operation_metadata_values():
    assert (
        CUA_OPERATION_METADATA.start_payload_error_message
        == "Failed to serialize CUA start params"
    )
    assert CUA_OPERATION_METADATA.start_operation_name == "cua start"
    assert CUA_OPERATION_METADATA.task_operation_name == "cua task"
    assert CUA_OPERATION_METADATA.status_operation_name == "cua task status"
    assert CUA_OPERATION_METADATA.stop_operation_name == "cua task stop"
    assert CUA_OPERATION_METADATA.start_error_message == "Failed to start CUA task job"
    assert CUA_OPERATION_METADATA.operation_name_prefix == "CUA task job "
