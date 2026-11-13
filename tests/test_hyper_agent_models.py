import pytest
from pydantic import ValidationError

from hyperbrowser.client._request import dump_request
from hyperbrowser.models.agents.hyper_agent import StartHyperAgentTaskParams


@pytest.mark.parametrize("llm", ["gpt-6.1-terra", "gpt-6-luna"])
def test_start_hyper_agent_accepts_gpt6_models(llm: str) -> None:
    dumped = dump_request(
        {"task": "Inspect the page", "llm": llm, "version": "1.1.0"},
        StartHyperAgentTaskParams,
    )
    assert dumped["llm"] == llm
    assert StartHyperAgentTaskParams(task="Inspect the page", llm=llm).llm == llm


def test_start_hyper_agent_rejects_unknown_model() -> None:
    with pytest.raises(ValidationError):
        StartHyperAgentTaskParams(task="Inspect the page", llm="gpt-6-orbit")
