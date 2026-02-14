import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.web_request_utils as web_request_utils


def test_start_web_job_builds_start_url_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "job-1"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = web_request_utils.parse_response_model
    web_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = web_request_utils.start_web_job(
            client=_Client(),
            route_prefix="/web/batch-fetch",
            payload={"urls": ["https://example.com"]},
            model=object,
            operation_name="batch fetch start",
        )
    finally:
        web_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/web/batch-fetch"
    assert captured["data"] == {"urls": ["https://example.com"]}
    assert captured["parse_data"] == {"id": "job-1"}
    assert captured["parse_kwargs"]["operation_name"] == "batch fetch start"


def test_get_web_job_status_builds_status_url_and_parses_response():
    captured = {}

    class _SyncTransport:
        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"status": "running"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = web_request_utils.parse_response_model
    web_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = web_request_utils.get_web_job_status(
            client=_Client(),
            route_prefix="/web/crawl",
            job_id="job-2",
            model=object,
            operation_name="web crawl status",
        )
    finally:
        web_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/web/crawl/job-2/status"
    assert captured["params"] is None
    assert captured["parse_data"] == {"status": "running"}
    assert captured["parse_kwargs"]["operation_name"] == "web crawl status"


def test_get_web_job_builds_job_url_and_passes_query_params():
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

    original_parse = web_request_utils.parse_response_model
    web_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = web_request_utils.get_web_job(
            client=_Client(),
            route_prefix="/web/batch-fetch",
            job_id="job-3",
            params={"page": 2},
            model=object,
            operation_name="batch fetch job",
        )
    finally:
        web_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/web/batch-fetch/job-3"
    assert captured["params"] == {"page": 2}
    assert captured["parse_data"] == {"data": []}
    assert captured["parse_kwargs"]["operation_name"] == "batch fetch job"


def test_start_web_job_async_builds_start_url_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "job-4"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = web_request_utils.parse_response_model
    web_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            web_request_utils.start_web_job_async(
                client=_Client(),
                route_prefix="/web/crawl",
                payload={"url": "https://example.com"},
                model=object,
                operation_name="web crawl start",
            )
        )
    finally:
        web_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/web/crawl"
    assert captured["data"] == {"url": "https://example.com"}
    assert captured["parse_data"] == {"id": "job-4"}
    assert captured["parse_kwargs"]["operation_name"] == "web crawl start"


def test_get_web_job_status_async_builds_status_url_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return SimpleNamespace(data={"status": "running"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = web_request_utils.parse_response_model
    web_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            web_request_utils.get_web_job_status_async(
                client=_Client(),
                route_prefix="/web/batch-fetch",
                job_id="job-5",
                model=object,
                operation_name="batch fetch status",
            )
        )
    finally:
        web_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/web/batch-fetch/job-5/status"
    assert captured["params"] is None
    assert captured["parse_data"] == {"status": "running"}
    assert captured["parse_kwargs"]["operation_name"] == "batch fetch status"


def test_get_web_job_async_builds_job_url_and_passes_query_params():
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

    original_parse = web_request_utils.parse_response_model
    web_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            web_request_utils.get_web_job_async(
                client=_Client(),
                route_prefix="/web/crawl",
                job_id="job-6",
                params={"batchSize": 10},
                model=object,
                operation_name="web crawl job",
            )
        )
    finally:
        web_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/web/crawl/job-6"
    assert captured["params"] == {"batchSize": 10}
    assert captured["parse_data"] == {"data": []}
    assert captured["parse_kwargs"]["operation_name"] == "web crawl job"
