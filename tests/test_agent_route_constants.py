from hyperbrowser.client.managers.agent_route_constants import (
    BROWSER_USE_TASK_ROUTE_PREFIX,
    CLAUDE_COMPUTER_USE_TASK_ROUTE_PREFIX,
    CUA_TASK_ROUTE_PREFIX,
    GEMINI_COMPUTER_USE_TASK_ROUTE_PREFIX,
    HYPER_AGENT_TASK_ROUTE_PREFIX,
)


def test_agent_route_constants_match_expected_api_paths():
    assert BROWSER_USE_TASK_ROUTE_PREFIX == "/task/browser-use"
    assert HYPER_AGENT_TASK_ROUTE_PREFIX == "/task/hyper-agent"
    assert GEMINI_COMPUTER_USE_TASK_ROUTE_PREFIX == "/task/gemini-computer-use"
    assert CLAUDE_COMPUTER_USE_TASK_ROUTE_PREFIX == "/task/claude-computer-use"
    assert CUA_TASK_ROUTE_PREFIX == "/task/cua"
