import asyncio

import hyperbrowser.client.managers.web_request_utils as web_request_utils


def test_start_web_job_delegates_to_start_job():
    captured = {}

    def _fake_start_job(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_start_job = web_request_utils.start_job
    web_request_utils.start_job = _fake_start_job
    try:
        result = web_request_utils.start_web_job(
            client=object(),
            route_prefix="/web/batch-fetch",
            payload={"urls": ["https://example.com"]},
            model=object,
            operation_name="batch fetch start",
        )
    finally:
        web_request_utils.start_job = original_start_job

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/web/batch-fetch"
    assert captured["payload"] == {"urls": ["https://example.com"]}
    assert captured["operation_name"] == "batch fetch start"


def test_get_web_job_status_delegates_to_get_job_status():
    captured = {}

    def _fake_get_job_status(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job_status = web_request_utils.get_job_status
    web_request_utils.get_job_status = _fake_get_job_status
    try:
        result = web_request_utils.get_web_job_status(
            client=object(),
            route_prefix="/web/crawl",
            job_id="job-2",
            model=object,
            operation_name="web crawl status",
        )
    finally:
        web_request_utils.get_job_status = original_get_job_status

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/web/crawl"
    assert captured["job_id"] == "job-2"
    assert captured["operation_name"] == "web crawl status"


def test_get_web_job_delegates_to_get_job():
    captured = {}

    def _fake_get_job(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job = web_request_utils.get_job
    web_request_utils.get_job = _fake_get_job
    try:
        result = web_request_utils.get_web_job(
            client=object(),
            route_prefix="/web/batch-fetch",
            job_id="job-3",
            params={"page": 2},
            model=object,
            operation_name="batch fetch job",
        )
    finally:
        web_request_utils.get_job = original_get_job

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/web/batch-fetch"
    assert captured["job_id"] == "job-3"
    assert captured["params"] == {"page": 2}
    assert captured["operation_name"] == "batch fetch job"


def test_start_web_job_async_delegates_to_start_job_async():
    captured = {}

    async def _fake_start_job_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_start_job_async = web_request_utils.start_job_async
    web_request_utils.start_job_async = _fake_start_job_async
    try:
        result = asyncio.run(
            web_request_utils.start_web_job_async(
                client=object(),
                route_prefix="/web/crawl",
                payload={"url": "https://example.com"},
                model=object,
                operation_name="web crawl start",
            )
        )
    finally:
        web_request_utils.start_job_async = original_start_job_async

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/web/crawl"
    assert captured["payload"] == {"url": "https://example.com"}
    assert captured["operation_name"] == "web crawl start"


def test_get_web_job_status_async_delegates_to_get_job_status_async():
    captured = {}

    async def _fake_get_job_status_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job_status_async = web_request_utils.get_job_status_async
    web_request_utils.get_job_status_async = _fake_get_job_status_async
    try:
        result = asyncio.run(
            web_request_utils.get_web_job_status_async(
                client=object(),
                route_prefix="/web/batch-fetch",
                job_id="job-5",
                model=object,
                operation_name="batch fetch status",
            )
        )
    finally:
        web_request_utils.get_job_status_async = original_get_job_status_async

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/web/batch-fetch"
    assert captured["job_id"] == "job-5"
    assert captured["operation_name"] == "batch fetch status"


def test_get_web_job_async_delegates_to_get_job_async():
    captured = {}

    async def _fake_get_job_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job_async = web_request_utils.get_job_async
    web_request_utils.get_job_async = _fake_get_job_async
    try:
        result = asyncio.run(
            web_request_utils.get_web_job_async(
                client=object(),
                route_prefix="/web/crawl",
                job_id="job-6",
                params={"batchSize": 10},
                model=object,
                operation_name="web crawl job",
            )
        )
    finally:
        web_request_utils.get_job_async = original_get_job_async

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/web/crawl"
    assert captured["job_id"] == "job-6"
    assert captured["params"] == {"batchSize": 10}
    assert captured["operation_name"] == "web crawl job"
