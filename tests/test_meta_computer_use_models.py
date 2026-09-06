from hyperbrowser.models.agents.meta_computer_use import MetaComputerUseTaskResponse


def test_meta_computer_use_task_response_parses_responses_style_step_payload() -> None:
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
                    "model": "muse-spark-1.1",
                    "output": [],
                    "reasoning": {"effort": "high"},
                    "status": "completed",
                }
            ],
            "finalResult": "result",
        },
    }

    result = MetaComputerUseTaskResponse(**payload)

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
