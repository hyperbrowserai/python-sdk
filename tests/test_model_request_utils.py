import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.model_request_utils as model_request_utils


def test_post_model_request_posts_payload_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "resource-1"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = model_request_utils.post_model_request(
            client=_Client(),
            route_path="/resource",
            data={"name": "value"},
            model=object,
            operation_name="create resource",
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource"
    assert captured["data"] == {"name": "value"}
    assert captured["parse_data"] == {"id": "resource-1"}
    assert captured["parse_kwargs"]["operation_name"] == "create resource"


def test_post_model_request_forwards_files_when_provided():
    captured = {}

    class _SyncTransport:
        def post(self, url, data, files=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return SimpleNamespace(data={"id": "resource-file"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = model_request_utils.post_model_request(
            client=_Client(),
            route_path="/resource",
            data={"name": "value"},
            files={"file": object()},
            model=object,
            operation_name="create resource",
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource"
    assert captured["files"] is not None
    assert captured["parse_data"] == {"id": "resource-file"}


def test_get_model_request_gets_payload_and_parses_response():
    captured = {}

    class _SyncTransport:
        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"id": "resource-2"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = model_request_utils.get_model_request(
            client=_Client(),
            route_path="/resource/2",
            params={"page": 1},
            model=object,
            operation_name="read resource",
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource/2"
    assert captured["params"] == {"page": 1}
    assert captured["parse_data"] == {"id": "resource-2"}
    assert captured["parse_kwargs"]["operation_name"] == "read resource"


def test_get_model_response_data_gets_payload_without_parsing():
    captured = {}

    class _SyncTransport:
        def get(self, url, params=None, follow_redirects=False):
            captured["url"] = url
            captured["params"] = params
            captured["follow_redirects"] = follow_redirects
            return SimpleNamespace(data={"id": "resource-raw"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = model_request_utils.get_model_response_data(
        client=_Client(),
        route_path="/resource/raw",
        params={"page": 1},
        follow_redirects=True,
    )

    assert result == {"id": "resource-raw"}
    assert captured["url"] == "https://api.example.test/resource/raw"
    assert captured["params"] == {"page": 1}
    assert captured["follow_redirects"] is True


def test_delete_model_request_deletes_resource_and_parses_response():
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

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = model_request_utils.delete_model_request(
            client=_Client(),
            route_path="/resource/3",
            model=object,
            operation_name="delete resource",
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource/3"
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "delete resource"


def test_post_model_request_async_posts_payload_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "resource-4"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            model_request_utils.post_model_request_async(
                client=_Client(),
                route_path="/resource",
                data={"name": "value"},
                model=object,
                operation_name="create resource",
            )
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource"
    assert captured["data"] == {"name": "value"}
    assert captured["parse_data"] == {"id": "resource-4"}
    assert captured["parse_kwargs"]["operation_name"] == "create resource"


def test_post_model_request_async_forwards_files_when_provided():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data, files=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return SimpleNamespace(data={"id": "resource-file-async"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            model_request_utils.post_model_request_async(
                client=_Client(),
                route_path="/resource",
                data={"name": "value"},
                files={"file": object()},
                model=object,
                operation_name="create resource",
            )
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource"
    assert captured["files"] is not None
    assert captured["parse_data"] == {"id": "resource-file-async"}


def test_get_model_request_async_gets_payload_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"id": "resource-5"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            model_request_utils.get_model_request_async(
                client=_Client(),
                route_path="/resource/5",
                params={"page": 2},
                model=object,
                operation_name="read resource",
            )
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource/5"
    assert captured["params"] == {"page": 2}
    assert captured["parse_data"] == {"id": "resource-5"}
    assert captured["parse_kwargs"]["operation_name"] == "read resource"


def test_get_model_response_data_async_gets_payload_without_parsing():
    captured = {}

    class _AsyncTransport:
        async def get(self, url, params=None, follow_redirects=False):
            captured["url"] = url
            captured["params"] = params
            captured["follow_redirects"] = follow_redirects
            return SimpleNamespace(data={"id": "resource-raw-async"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = asyncio.run(
        model_request_utils.get_model_response_data_async(
            client=_Client(),
            route_path="/resource/raw",
            params={"page": 2},
            follow_redirects=True,
        )
    )

    assert result == {"id": "resource-raw-async"}
    assert captured["url"] == "https://api.example.test/resource/raw"
    assert captured["params"] == {"page": 2}
    assert captured["follow_redirects"] is True


def test_delete_model_request_async_deletes_resource_and_parses_response():
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

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            model_request_utils.delete_model_request_async(
                client=_Client(),
                route_path="/resource/6",
                model=object,
                operation_name="delete resource",
            )
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/resource/6"
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "delete resource"


def test_post_model_request_to_endpoint_posts_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, endpoint, data):
            captured["endpoint"] = endpoint
            captured["data"] = data
            return SimpleNamespace(data={"id": "endpoint-resource"})

    class _Client:
        transport = _SyncTransport()

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = model_request_utils.post_model_request_to_endpoint(
            client=_Client(),
            endpoint="https://api.example.test/resource",
            data={"name": "value"},
            model=object,
            operation_name="endpoint create",
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["endpoint"] == "https://api.example.test/resource"
    assert captured["data"] == {"name": "value"}
    assert captured["parse_data"] == {"id": "endpoint-resource"}
    assert captured["parse_kwargs"]["operation_name"] == "endpoint create"


def test_post_model_request_to_endpoint_async_posts_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, endpoint, data):
            captured["endpoint"] = endpoint
            captured["data"] = data
            return SimpleNamespace(data={"id": "endpoint-resource-async"})

    class _Client:
        transport = _AsyncTransport()

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = model_request_utils.parse_response_model
    model_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            model_request_utils.post_model_request_to_endpoint_async(
                client=_Client(),
                endpoint="https://api.example.test/resource",
                data={"name": "value"},
                model=object,
                operation_name="endpoint create",
            )
        )
    finally:
        model_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["endpoint"] == "https://api.example.test/resource"
    assert captured["data"] == {"name": "value"}
    assert captured["parse_data"] == {"id": "endpoint-resource-async"}
    assert captured["parse_kwargs"]["operation_name"] == "endpoint create"
