import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.session_request_utils as session_request_utils


def test_post_session_resource_forwards_payload():
    captured = {}

    class _SyncTransport:
        def post(self, url, data=None, files=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return SimpleNamespace(data={"ok": True})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = session_request_utils.post_session_resource(
        client=_Client(),
        route_path="/session",
        data={"useStealth": True},
    )

    assert result == {"ok": True}
    assert captured["url"] == "https://api.example.test/session"
    assert captured["data"] == {"useStealth": True}
    assert captured["files"] is None


def test_get_session_resource_supports_follow_redirects():
    captured = {}

    class _SyncTransport:
        def get(self, url, params=None, *args):
            captured["url"] = url
            captured["params"] = params
            captured["args"] = args
            return SimpleNamespace(data={"ok": True})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = session_request_utils.get_session_resource(
        client=_Client(),
        route_path="/session/sess_1/recording",
        follow_redirects=True,
    )

    assert result == {"ok": True}
    assert captured["url"] == "https://api.example.test/session/sess_1/recording"
    assert captured["params"] is None
    assert captured["args"] == (True,)


def test_put_session_resource_forwards_payload():
    captured = {}

    class _SyncTransport:
        def put(self, url, data=None):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"ok": True})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = session_request_utils.put_session_resource(
        client=_Client(),
        route_path="/session/sess_1/extend-session",
        data={"durationMinutes": 10},
    )

    assert result == {"ok": True}
    assert captured["url"] == "https://api.example.test/session/sess_1/extend-session"
    assert captured["data"] == {"durationMinutes": 10}


def test_post_session_resource_async_forwards_payload():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data=None, files=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return SimpleNamespace(data={"ok": True})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = asyncio.run(
        session_request_utils.post_session_resource_async(
            client=_Client(),
            route_path="/session",
            data={"useStealth": True},
        )
    )

    assert result == {"ok": True}
    assert captured["url"] == "https://api.example.test/session"
    assert captured["data"] == {"useStealth": True}
    assert captured["files"] is None


def test_get_session_resource_async_supports_follow_redirects():
    captured = {}

    class _AsyncTransport:
        async def get(self, url, params=None, *args):
            captured["url"] = url
            captured["params"] = params
            captured["args"] = args
            return SimpleNamespace(data={"ok": True})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = asyncio.run(
        session_request_utils.get_session_resource_async(
            client=_Client(),
            route_path="/session/sess_1/recording",
            follow_redirects=True,
        )
    )

    assert result == {"ok": True}
    assert captured["url"] == "https://api.example.test/session/sess_1/recording"
    assert captured["params"] is None
    assert captured["args"] == (True,)


def test_put_session_resource_async_forwards_payload():
    captured = {}

    class _AsyncTransport:
        async def put(self, url, data=None):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"ok": True})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = asyncio.run(
        session_request_utils.put_session_resource_async(
            client=_Client(),
            route_path="/session/sess_1/extend-session",
            data={"durationMinutes": 10},
        )
    )

    assert result == {"ok": True}
    assert captured["url"] == "https://api.example.test/session/sess_1/extend-session"
    assert captured["data"] == {"durationMinutes": 10}
