import asyncio

import hyperbrowser.client.managers.team_request_utils as team_request_utils


def test_get_team_resource_delegates_to_get_model_request():
    captured = {}

    def _fake_get_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = team_request_utils.get_model_request
    team_request_utils.get_model_request = _fake_get_model_request
    try:
        result = team_request_utils.get_team_resource(
            client=object(),
            route_path="/team/credit-info",
            model=object,
            operation_name="team credit info",
        )
    finally:
        team_request_utils.get_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/team/credit-info"
    assert captured["params"] is None
    assert captured["operation_name"] == "team credit info"


def test_get_team_resource_async_delegates_to_get_model_request_async():
    captured = {}

    async def _fake_get_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = team_request_utils.get_model_request_async
    team_request_utils.get_model_request_async = _fake_get_model_request_async
    try:
        result = asyncio.run(
            team_request_utils.get_team_resource_async(
                client=object(),
                route_path="/team/credit-info",
                model=object,
                operation_name="team credit info",
            )
        )
    finally:
        team_request_utils.get_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/team/credit-info"
    assert captured["params"] is None
    assert captured["operation_name"] == "team credit info"
