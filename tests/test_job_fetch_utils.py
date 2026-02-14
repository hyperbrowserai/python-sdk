import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.job_fetch_utils as job_fetch_utils
from hyperbrowser.client.managers.polling_defaults import (
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLLING_RETRY_DELAY_SECONDS,
)


def test_retry_operation_with_defaults_forwards_arguments() -> None:
    captured_kwargs = {}

    def _fake_retry_operation(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return {"ok": True}

    original_retry = job_fetch_utils.retry_operation
    job_fetch_utils.retry_operation = _fake_retry_operation
    try:
        result = job_fetch_utils.retry_operation_with_defaults(
            operation_name="fetch job",
            operation=lambda: {"job_id": "abc"},
        )
    finally:
        job_fetch_utils.retry_operation = original_retry

    assert result == {"ok": True}
    assert captured_kwargs["operation_name"] == "fetch job"
    assert captured_kwargs["max_attempts"] == DEFAULT_POLLING_RETRY_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == DEFAULT_POLLING_RETRY_DELAY_SECONDS


def test_retry_operation_with_defaults_async_forwards_arguments() -> None:
    captured_kwargs = {}

    async def _fake_retry_operation_async(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return {"ok": True}

    original_retry = job_fetch_utils.retry_operation_async
    job_fetch_utils.retry_operation_async = _fake_retry_operation_async
    try:
        result = asyncio.run(
            job_fetch_utils.retry_operation_with_defaults_async(
                operation_name="fetch job",
                operation=lambda: asyncio.sleep(0, result={"job_id": "abc"}),
            )
        )
    finally:
        job_fetch_utils.retry_operation_async = original_retry

    assert result == {"ok": True}
    assert captured_kwargs["operation_name"] == "fetch job"
    assert captured_kwargs["max_attempts"] == DEFAULT_POLLING_RETRY_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == DEFAULT_POLLING_RETRY_DELAY_SECONDS


def test_collect_paginated_results_with_defaults_forwards_arguments() -> None:
    captured_kwargs = {}

    def _fake_collect_paginated_results(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return None

    original_collect = job_fetch_utils.collect_paginated_results
    job_fetch_utils.collect_paginated_results = _fake_collect_paginated_results
    try:
        result = job_fetch_utils.collect_paginated_results_with_defaults(
            operation_name="batch job",
            get_next_page=lambda page: {"page": page},
            get_current_page_batch=lambda response: response["page"],
            get_total_page_batches=lambda response: response["page"] + 1,
            on_page_success=lambda response: None,
            max_wait_seconds=25.0,
        )
    finally:
        job_fetch_utils.collect_paginated_results = original_collect

    assert result is None
    assert captured_kwargs["operation_name"] == "batch job"
    assert captured_kwargs["max_wait_seconds"] == 25.0
    assert captured_kwargs["max_attempts"] == DEFAULT_POLLING_RETRY_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == DEFAULT_POLLING_RETRY_DELAY_SECONDS


def test_collect_paginated_results_with_defaults_async_forwards_arguments() -> None:
    captured_kwargs = {}

    async def _fake_collect_paginated_results_async(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return None

    original_collect = job_fetch_utils.collect_paginated_results_async
    job_fetch_utils.collect_paginated_results_async = _fake_collect_paginated_results_async
    try:
        result = asyncio.run(
            job_fetch_utils.collect_paginated_results_with_defaults_async(
                operation_name="batch job",
                get_next_page=lambda page: asyncio.sleep(0, result={"page": page}),
                get_current_page_batch=lambda response: response["page"],
                get_total_page_batches=lambda response: response["page"] + 1,
                on_page_success=lambda response: None,
                max_wait_seconds=25.0,
            )
        )
    finally:
        job_fetch_utils.collect_paginated_results_async = original_collect

    assert result is None
    assert captured_kwargs["operation_name"] == "batch job"
    assert captured_kwargs["max_wait_seconds"] == 25.0
    assert captured_kwargs["max_attempts"] == DEFAULT_POLLING_RETRY_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == DEFAULT_POLLING_RETRY_DELAY_SECONDS


def test_fetch_job_result_with_defaults_uses_fetch_operation_name() -> None:
    captured_kwargs = {}

    def _fake_retry_operation_with_defaults(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return {"ok": True}

    original_retry = job_fetch_utils.retry_operation_with_defaults
    job_fetch_utils.retry_operation_with_defaults = _fake_retry_operation_with_defaults
    try:
        result = job_fetch_utils.fetch_job_result_with_defaults(
            operation_name="crawl job abc",
            fetch_result=lambda: {"payload": True},
        )
    finally:
        job_fetch_utils.retry_operation_with_defaults = original_retry

    assert result == {"ok": True}
    assert captured_kwargs["operation_name"] == "Fetching crawl job abc"


def test_fetch_job_result_with_defaults_async_uses_fetch_operation_name() -> None:
    captured_kwargs = {}

    async def _fake_retry_operation_with_defaults_async(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return {"ok": True}

    original_retry = job_fetch_utils.retry_operation_with_defaults_async
    job_fetch_utils.retry_operation_with_defaults_async = (
        _fake_retry_operation_with_defaults_async
    )
    try:
        result = asyncio.run(
            job_fetch_utils.fetch_job_result_with_defaults_async(
                operation_name="crawl job abc",
                fetch_result=lambda: asyncio.sleep(0, result={"payload": True}),
            )
        )
    finally:
        job_fetch_utils.retry_operation_with_defaults_async = original_retry

    assert result == {"ok": True}
    assert captured_kwargs["operation_name"] == "Fetching crawl job abc"


def test_read_page_current_batch_reads_attribute() -> None:
    response = SimpleNamespace(current_page_batch=3)

    result = job_fetch_utils.read_page_current_batch(response)

    assert result == 3


def test_read_page_total_batches_reads_attribute() -> None:
    response = SimpleNamespace(total_page_batches=7)

    result = job_fetch_utils.read_page_total_batches(response)

    assert result == 7
