import pytest
from pydantic import ValidationError

from hyperbrowser.client._request import dump_request
from hyperbrowser.models.agents.grok_computer_use import (
    GrokComputerUseTaskResponse,
    StartGrokComputerUseTaskParams,
)


def test_grok_computer_use_task_response_parses_xai_style_step_payload() -> None:
    payload = {
        "jobId": "job-123",
        "status": "completed",
        "data": {
            "steps": [
                {
                    "created_at": 1710000000,
                    "completed_at": 1710000001,
                    "output_text": "done",
                    "error": {"code": "ERR", "message": "something failed"},
                    "incomplete_details": {"reason": "timeout"},
                    "model": "grok-4.5",
                    "output": [],
                    "reasoning": {"effort": "high"},
                    "status": "completed",
                }
            ],
            "finalResult": "result",
        },
    }

    result = GrokComputerUseTaskResponse(**payload)

    step = result.data.steps[0]
    assert step.created_at == 1710000000
    assert step.completed_at == 1710000001
    assert step.error is not None
    assert step.error.code == "ERR"
    assert step.error.message == "something failed"
    assert step.incomplete_details is not None
    assert step.incomplete_details.reason == "timeout"
    assert step.reasoning is not None
    assert step.reasoning.effort == "high"


@pytest.mark.parametrize("llm", ["grok-4.7", "grok-4.6", "grok-4.5"])
def test_start_grok_computer_use_accepts_api_models(llm: str) -> None:
    model_params = StartGrokComputerUseTaskParams(task="Inspect the page", llm=llm)
    dict_params = {"task": "Inspect the page", "llm": llm}

    for params in (model_params, dict_params):
        dumped = dump_request(params, StartGrokComputerUseTaskParams)
        assert dumped["task"] == "Inspect the page"
        assert dumped["llm"] == llm


def test_start_grok_computer_use_rejects_unknown_model() -> None:
    with pytest.raises(ValidationError):
        StartGrokComputerUseTaskParams(task="Inspect the page", llm="grok-4")
