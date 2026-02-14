import asyncio

import hyperbrowser.client.managers.job_request_utils as job_request_utils


def test_start_job_delegates_to_post_model_request():
    captured = {}

    def _fake_post_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.post_model_request
    job_request_utils.post_model_request = _fake_post_model_request
    try:
        result = job_request_utils.start_job(
            client=object(),
            route_prefix="/scrape",
            payload={"url": "https://example.com"},
            model=object,
            operation_name="scrape start",
        )
    finally:
        job_request_utils.post_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/scrape"
    assert captured["data"] == {"url": "https://example.com"}
    assert captured["operation_name"] == "scrape start"


def test_get_job_status_delegates_to_get_model_request():
    captured = {}

    def _fake_get_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.get_model_request
    job_request_utils.get_model_request = _fake_get_model_request
    try:
        result = job_request_utils.get_job_status(
            client=object(),
            route_prefix="/crawl",
            job_id="job-2",
            model=object,
            operation_name="crawl status",
        )
    finally:
        job_request_utils.get_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/crawl/job-2/status"
    assert captured["params"] is None
    assert captured["operation_name"] == "crawl status"


def test_get_job_delegates_to_get_model_request():
    captured = {}

    def _fake_get_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.get_model_request
    job_request_utils.get_model_request = _fake_get_model_request
    try:
        result = job_request_utils.get_job(
            client=object(),
            route_prefix="/scrape/batch",
            job_id="job-3",
            params={"page": 2},
            model=object,
            operation_name="batch scrape job",
        )
    finally:
        job_request_utils.get_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/scrape/batch/job-3"
    assert captured["params"] == {"page": 2}
    assert captured["operation_name"] == "batch scrape job"


def test_start_job_async_delegates_to_post_model_request_async():
    captured = {}

    async def _fake_post_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.post_model_request_async
    job_request_utils.post_model_request_async = _fake_post_model_request_async
    try:
        result = asyncio.run(
            job_request_utils.start_job_async(
                client=object(),
                route_prefix="/extract",
                payload={"url": "https://example.com"},
                model=object,
                operation_name="extract start",
            )
        )
    finally:
        job_request_utils.post_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/extract"
    assert captured["data"] == {"url": "https://example.com"}
    assert captured["operation_name"] == "extract start"


def test_get_job_status_async_delegates_to_get_model_request_async():
    captured = {}

    async def _fake_get_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.get_model_request_async
    job_request_utils.get_model_request_async = _fake_get_model_request_async
    try:
        result = asyncio.run(
            job_request_utils.get_job_status_async(
                client=object(),
                route_prefix="/scrape",
                job_id="job-5",
                model=object,
                operation_name="scrape status",
            )
        )
    finally:
        job_request_utils.get_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/scrape/job-5/status"
    assert captured["params"] is None
    assert captured["operation_name"] == "scrape status"


def test_get_job_async_delegates_to_get_model_request_async():
    captured = {}

    async def _fake_get_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.get_model_request_async
    job_request_utils.get_model_request_async = _fake_get_model_request_async
    try:
        result = asyncio.run(
            job_request_utils.get_job_async(
                client=object(),
                route_prefix="/crawl",
                job_id="job-6",
                params={"batchSize": 10},
                model=object,
                operation_name="crawl job",
            )
        )
    finally:
        job_request_utils.get_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/crawl/job-6"
    assert captured["params"] == {"batchSize": 10}
    assert captured["operation_name"] == "crawl job"


def test_put_job_action_delegates_to_put_model_request():
    captured = {}

    def _fake_put_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.put_model_request
    job_request_utils.put_model_request = _fake_put_model_request
    try:
        result = job_request_utils.put_job_action(
            client=object(),
            route_prefix="/task/cua",
            job_id="job-7",
            action_suffix="/stop",
            model=object,
            operation_name="cua task stop",
        )
    finally:
        job_request_utils.put_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/task/cua/job-7/stop"
    assert captured["data"] is None
    assert captured["operation_name"] == "cua task stop"


def test_put_job_action_async_delegates_to_put_model_request_async():
    captured = {}

    async def _fake_put_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = job_request_utils.put_model_request_async
    job_request_utils.put_model_request_async = _fake_put_model_request_async
    try:
        result = asyncio.run(
            job_request_utils.put_job_action_async(
                client=object(),
                route_prefix="/task/hyper-agent",
                job_id="job-8",
                action_suffix="/stop",
                model=object,
                operation_name="hyper-agent task stop",
            )
        )
    finally:
        job_request_utils.put_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/task/hyper-agent/job-8/stop"
    assert captured["data"] is None
    assert captured["operation_name"] == "hyper-agent task stop"
