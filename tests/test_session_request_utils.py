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
        def get(self, url, params=None, follow_redirects=False):
            captured["url"] = url
            captured["params"] = params
            captured["follow_redirects"] = follow_redirects
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
    assert captured["follow_redirects"] is True


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
        async def get(self, url, params=None, follow_redirects=False):
            captured["url"] = url
            captured["params"] = params
            captured["follow_redirects"] = follow_redirects
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
    assert captured["follow_redirects"] is True


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


def test_post_session_model_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, url, data=None, files=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return SimpleNamespace(data={"jobId": "sess_1"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_session_response_model(response_data, *, model, operation_name):
        captured["parse_response_data"] = response_data
        captured["parse_model"] = model
        captured["parse_operation_name"] = operation_name
        return {"parsed": True}

    original_parse = session_request_utils.parse_session_response_model
    session_request_utils.parse_session_response_model = _fake_parse_session_response_model
    try:
        result = session_request_utils.post_session_model(
            client=_Client(),
            route_path="/session",
            data={"useStealth": True},
            model=object,
            operation_name="session detail",
        )
    finally:
        session_request_utils.parse_session_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/session"
    assert captured["data"] == {"useStealth": True}
    assert captured["files"] is None
    assert captured["parse_response_data"] == {"jobId": "sess_1"}
    assert captured["parse_model"] is object
    assert captured["parse_operation_name"] == "session detail"


def test_get_session_recordings_parses_recording_payload():
    captured = {}

    class _SyncTransport:
        def get(self, url, params=None, follow_redirects=False):
            captured["url"] = url
            captured["params"] = params
            captured["follow_redirects"] = follow_redirects
            return SimpleNamespace(data=[{"id": "rec_1"}])

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_session_recordings_response_data(response_data):
        captured["parse_response_data"] = response_data
        return ["parsed-recording"]

    original_parse = session_request_utils.parse_session_recordings_response_data
    session_request_utils.parse_session_recordings_response_data = (
        _fake_parse_session_recordings_response_data
    )
    try:
        result = session_request_utils.get_session_recordings(
            client=_Client(),
            route_path="/session/sess_1/recording",
        )
    finally:
        session_request_utils.parse_session_recordings_response_data = original_parse

    assert result == ["parsed-recording"]
    assert captured["url"] == "https://api.example.test/session/sess_1/recording"
    assert captured["params"] is None
    assert captured["follow_redirects"] is True
    assert captured["parse_response_data"] == [{"id": "rec_1"}]


def test_put_session_model_async_parses_response():
    captured = {}

    class _AsyncTransport:
        async def put(self, url, data=None):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"success": True})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_session_response_model(response_data, *, model, operation_name):
        captured["parse_response_data"] = response_data
        captured["parse_model"] = model
        captured["parse_operation_name"] = operation_name
        return {"parsed": True}

    original_parse = session_request_utils.parse_session_response_model
    session_request_utils.parse_session_response_model = _fake_parse_session_response_model
    try:
        result = asyncio.run(
            session_request_utils.put_session_model_async(
                client=_Client(),
                route_path="/session/sess_1/stop",
                model=object,
                operation_name="session stop",
            )
        )
    finally:
        session_request_utils.parse_session_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/session/sess_1/stop"
    assert captured["data"] is None
    assert captured["parse_response_data"] == {"success": True}
    assert captured["parse_model"] is object
    assert captured["parse_operation_name"] == "session stop"
