import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.job_request_utils as job_request_utils


def test_start_job_builds_start_url_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"jobId": "job-1"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = job_request_utils.start_job(
            client=_Client(),
            route_prefix="/scrape",
            payload={"url": "https://example.com"},
            model=object,
            operation_name="scrape start",
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/scrape"
    assert captured["data"] == {"url": "https://example.com"}
    assert captured["parse_data"] == {"jobId": "job-1"}
    assert captured["parse_kwargs"]["operation_name"] == "scrape start"


def test_get_job_status_builds_status_url_and_parses_response():
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

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = job_request_utils.get_job_status(
            client=_Client(),
            route_prefix="/crawl",
            job_id="job-2",
            model=object,
            operation_name="crawl status",
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/crawl/job-2/status"
    assert captured["params"] is None
    assert captured["parse_data"] == {"status": "running"}
    assert captured["parse_kwargs"]["operation_name"] == "crawl status"


def test_get_job_builds_job_url_and_passes_query_params():
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

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = job_request_utils.get_job(
            client=_Client(),
            route_prefix="/scrape/batch",
            job_id="job-3",
            params={"page": 2},
            model=object,
            operation_name="batch scrape job",
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/scrape/batch/job-3"
    assert captured["params"] == {"page": 2}
    assert captured["parse_data"] == {"data": []}
    assert captured["parse_kwargs"]["operation_name"] == "batch scrape job"


def test_start_job_async_builds_start_url_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"jobId": "job-4"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            job_request_utils.start_job_async(
                client=_Client(),
                route_prefix="/extract",
                payload={"url": "https://example.com"},
                model=object,
                operation_name="extract start",
            )
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/extract"
    assert captured["data"] == {"url": "https://example.com"}
    assert captured["parse_data"] == {"jobId": "job-4"}
    assert captured["parse_kwargs"]["operation_name"] == "extract start"


def test_get_job_status_async_builds_status_url_and_parses_response():
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

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            job_request_utils.get_job_status_async(
                client=_Client(),
                route_prefix="/scrape",
                job_id="job-5",
                model=object,
                operation_name="scrape status",
            )
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/scrape/job-5/status"
    assert captured["params"] is None
    assert captured["parse_data"] == {"status": "running"}
    assert captured["parse_kwargs"]["operation_name"] == "scrape status"


def test_get_job_async_builds_job_url_and_passes_query_params():
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

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            job_request_utils.get_job_async(
                client=_Client(),
                route_prefix="/crawl",
                job_id="job-6",
                params={"batchSize": 10},
                model=object,
                operation_name="crawl job",
            )
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/crawl/job-6"
    assert captured["params"] == {"batchSize": 10}
    assert captured["parse_data"] == {"data": []}
    assert captured["parse_kwargs"]["operation_name"] == "crawl job"


def test_put_job_action_builds_action_url_and_parses_response():
    captured = {}

    class _SyncTransport:
        def put(self, url):
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

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = job_request_utils.put_job_action(
            client=_Client(),
            route_prefix="/task/cua",
            job_id="job-7",
            action_suffix="/stop",
            model=object,
            operation_name="cua task stop",
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/task/cua/job-7/stop"
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "cua task stop"


def test_put_job_action_async_builds_action_url_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def put(self, url):
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

    original_parse = job_request_utils.parse_response_model
    job_request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            job_request_utils.put_job_action_async(
                client=_Client(),
                route_prefix="/task/hyper-agent",
                job_id="job-8",
                action_suffix="/stop",
                model=object,
                operation_name="hyper-agent task stop",
            )
        )
    finally:
        job_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/task/hyper-agent/job-8/stop"
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "hyper-agent task stop"
