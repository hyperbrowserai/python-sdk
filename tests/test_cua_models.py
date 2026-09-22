import pytest
from pydantic import ValidationError

from hyperbrowser.client._request import dump_request
from hyperbrowser.models.agents.cua import StartCuaTaskParams


@pytest.mark.parametrize("llm", ["gpt-6-sol", "gpt-6-luna", "gpt-6-astra"])
def test_start_cua_accepts_gpt6_models(llm: str) -> None:
    dumped = dump_request(
        {"task": "Inspect the page", "llm": llm, "reasoning_effort": "max"},
        StartCuaTaskParams,
    )
    assert dumped["llm"] == llm
    assert dumped["reasoningEffort"] == "max"


def test_start_cua_rejects_unknown_model() -> None:
    with pytest.raises(ValidationError):
        StartCuaTaskParams(task="Inspect the page", llm="gpt-6-orbit")
