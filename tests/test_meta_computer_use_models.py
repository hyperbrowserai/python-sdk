from hyperbrowser.models.agents.meta_computer_use import MetaComputerUseTaskResponse


def test_meta_computer_use_task_response_parses_responses_style_step_payload() -> None:
    payload = {
        "jobId": "job-123",
        "status": "completed",
        "data": {
            "steps": [
                {
                    "created_at": 1788743504,
                    "completed_at": 1788743511,
                    "output_text": (
                        "Second sentence in the Ecology section "
                        '(Population subsection) of the Dog Wikipedia page:\n\n'
                        '"In 2020, the estimated global dog population was '
                        'between 700 million and 1 billion."'
                    ),
                    "error": None,
                    "incomplete_details": None,
                    "model": "muse-spark-1.3",
                    "output": [
                        {
                            "type": "reasoning",
                            "status": "completed",
                            "summary": [
                                {
                                    "text": "Interpreting the ecology section structure.",
                                    "type": "summary_text",
                                }
                            ],
                        },
                        {
                            "type": "message",
                            "role": "assistant",
                            "status": "completed",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "Second sentence in the Ecology section.",
                                }
                            ],
                        },
                    ],
                    "reasoning": {
                        "effort": "medium",
                        "summary": "concise",
                    },
                    "status": "completed",
                },
                {
                    "created_at": 1788743409,
                    "completed_at": 1788743410,
                    "output_text": "",
                    "error": {"code": "ERR", "message": "something failed"},
                    "incomplete_details": {"reason": "timeout"},
                    "model": "muse-spark-1.3",
                    "output": [
                        {
                            "type": "function_call",
                            "name": "computer.computer",
                            "arguments": '{"actions":[{"action":"type","text":"google.com\\n"}]}',
                            "status": "completed",
                        }
                    ],
                    "reasoning": {"effort": "medium", "summary": "concise"},
                    "status": "completed",
                },
            ],
            "finalResult": "result",
        },
    }

    result = MetaComputerUseTaskResponse(**payload)

    final_step = result.data.steps[0]
    assert final_step.created_at == 1788743504
    assert final_step.completed_at == 1788743511
    assert final_step.error is None
    assert final_step.incomplete_details is None
    assert final_step.model == "muse-spark-1.3"
    assert final_step.reasoning is not None
    assert final_step.reasoning.effort == "medium"
    assert final_step.reasoning.summary == "concise"
    assert final_step.output[0]["type"] == "reasoning"
    assert final_step.output[1]["type"] == "message"

    action_step = result.data.steps[1]
    assert action_step.error is not None
    assert action_step.error.code == "ERR"
    assert action_step.error.message == "something failed"
    assert action_step.incomplete_details is not None
    assert action_step.incomplete_details.reason == "timeout"
    assert action_step.output[0]["name"] == "computer.computer"
