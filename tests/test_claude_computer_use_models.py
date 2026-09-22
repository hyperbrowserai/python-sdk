from hyperbrowser.client._request import dump_request
from hyperbrowser.models.agents.claude_computer_use import (
    StartClaudeComputerUseTaskParams,
)


def test_start_claude_computer_use_accepts_opus_5_5() -> None:
    dumped = dump_request(
        {
            "task": "Inspect the page",
            "llm": "claude-opus-5-5",
            "reasoning_effort": "max",
        },
        StartClaudeComputerUseTaskParams,
    )
    assert dumped["llm"] == "claude-opus-5-5"
    assert dumped["reasoningEffort"] == "max"
