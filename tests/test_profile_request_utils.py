import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.profile_request_utils as profile_request_utils


def test_create_profile_resource_uses_post_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "profile-1"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = profile_request_utils.create_profile_resource(
            client=_Client(),
            route_prefix="/profile",
            payload={"name": "test"},
            model=object,
            operation_name="create profile",
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profile"
    assert captured["data"] == {"name": "test"}
    assert captured["parse_data"] == {"id": "profile-1"}
    assert captured["parse_kwargs"]["operation_name"] == "create profile"


def test_get_profile_resource_uses_get_and_parses_response():
    captured = {}

    class _SyncTransport:
        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"id": "profile-2"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = profile_request_utils.get_profile_resource(
            client=_Client(),
            profile_id="profile-2",
            model=object,
            operation_name="get profile",
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profile/profile-2"
    assert captured["params"] is None
    assert captured["parse_data"] == {"id": "profile-2"}
    assert captured["parse_kwargs"]["operation_name"] == "get profile"


def test_delete_profile_resource_uses_delete_and_parses_response():
    captured = {}

    class _SyncTransport:
        def delete(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"success": True})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = profile_request_utils.delete_profile_resource(
            client=_Client(),
            profile_id="profile-3",
            model=object,
            operation_name="delete profile",
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profile/profile-3"
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "delete profile"


def test_list_profile_resources_uses_get_with_params_and_parses_response():
    captured = {}

    class _SyncTransport:
        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"data": []})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = profile_request_utils.list_profile_resources(
            client=_Client(),
            list_route_path="/profiles",
            params={"page": 1},
            model=object,
            operation_name="list profiles",
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profiles"
    assert captured["params"] == {"page": 1}
    assert captured["parse_data"] == {"data": []}
    assert captured["parse_kwargs"]["operation_name"] == "list profiles"


def test_create_profile_resource_async_uses_post_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "profile-4"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            profile_request_utils.create_profile_resource_async(
                client=_Client(),
                route_prefix="/profile",
                payload={"name": "async"},
                model=object,
                operation_name="create profile",
            )
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profile"
    assert captured["data"] == {"name": "async"}
    assert captured["parse_data"] == {"id": "profile-4"}
    assert captured["parse_kwargs"]["operation_name"] == "create profile"


def test_get_profile_resource_async_uses_get_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"id": "profile-5"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            profile_request_utils.get_profile_resource_async(
                client=_Client(),
                profile_id="profile-5",
                model=object,
                operation_name="get profile",
            )
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profile/profile-5"
    assert captured["params"] is None
    assert captured["parse_data"] == {"id": "profile-5"}
    assert captured["parse_kwargs"]["operation_name"] == "get profile"


def test_delete_profile_resource_async_uses_delete_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def delete(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"success": True})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            profile_request_utils.delete_profile_resource_async(
                client=_Client(),
                profile_id="profile-6",
                model=object,
                operation_name="delete profile",
            )
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profile/profile-6"
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "delete profile"


def test_list_profile_resources_async_uses_get_with_params_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"data": []})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = profile_request_utils.parse_response_model
    profile_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            profile_request_utils.list_profile_resources_async(
                client=_Client(),
                list_route_path="/profiles",
                params={"page": 2},
                model=object,
                operation_name="list profiles",
            )
        )
    finally:
        profile_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/profiles"
    assert captured["params"] == {"page": 2}
    assert captured["parse_data"] == {"data": []}
    assert captured["parse_kwargs"]["operation_name"] == "list profiles"
