import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.team_request_utils as team_request_utils


def test_get_team_resource_uses_route_and_parses_response():
    captured = {}

    class _SyncTransport:
        def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"remainingCredits": 42})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = team_request_utils.parse_response_model
    team_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = team_request_utils.get_team_resource(
            client=_Client(),
            route_path="/team/credit-info",
            model=object,
            operation_name="team credit info",
        )
    finally:
        team_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/team/credit-info"
    assert captured["parse_data"] == {"remainingCredits": 42}
    assert captured["parse_kwargs"]["operation_name"] == "team credit info"


def test_get_team_resource_async_uses_route_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"remainingCredits": 42})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = team_request_utils.parse_response_model
    team_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            team_request_utils.get_team_resource_async(
                client=_Client(),
                route_path="/team/credit-info",
                model=object,
                operation_name="team credit info",
            )
        )
    finally:
        team_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/team/credit-info"
    assert captured["parse_data"] == {"remainingCredits": 42}
    assert captured["parse_kwargs"]["operation_name"] == "team credit info"
