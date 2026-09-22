import pytest
from pydantic import ValidationError

from hyperbrowser.client._request import dump_request
from hyperbrowser.models.agents.jev_computer_use import (
    JevComputerUseTaskResponse,
    StartJevComputerUseTaskParams,
)


def test_jev_computer_use_task_response_parses_step_payload() -> None:
    payload = {
        "jobId": "job-123",
        "status": "completed",
        "data": {
            "steps": [
                {
                    "step": 1,
                    "action": {"kind": "click", "target": "submit"},
                    "url": "https://example.com",
                    "title": "Example",
                    "pageText": "Order details",
                    "targetDescription": "Submit button",
                    "confidence": 0.91,
                    "outcome": "dispatched",
                    "pageChanged": True,
                    "beforeObservation": 0,
                    "afterObservation": 1,
                }
            ],
            "finalResult": "Found the order",
        },
    }

    result = JevComputerUseTaskResponse(**payload)

    step = result.data.steps[0]
    assert isinstance(step, dict)
    assert step["step"] == 1
    assert step["action"] == {"kind": "click", "target": "submit"}
    assert step["pageText"] == "Order details"
    assert result.data.final_result == "Found the order"
    assert not hasattr(result.data, "final_url")
    assert not hasattr(result.data, "reached_max_steps")
    assert not hasattr(result.data, "warnings")


@pytest.mark.parametrize("llm", ["jev-1.13.0", "jev-latest"])
def test_start_jev_computer_use_accepts_api_models(llm: str) -> None:
    model_params = StartJevComputerUseTaskParams(
        task="Find the order",
        llm=llm,
        text_llm="gemini-3.5-flash-lite",
    )
    dict_params = {
        "task": "Find the order",
        "llm": llm,
        "text_llm": "gemini-3.5-flash-lite",
    }

    for params in (model_params, dict_params):
        dumped = dump_request(params, StartJevComputerUseTaskParams)
        assert dumped["task"] == "Find the order"
        assert dumped["llm"] == llm
        assert dumped["textLlm"] == "gemini-3.5-flash-lite"
        assert "startUrl" not in dumped


def test_start_jev_computer_use_rejects_unknown_model() -> None:
    with pytest.raises(ValidationError):
        StartJevComputerUseTaskParams(task="Find the order", llm="jev-1.0.0")
