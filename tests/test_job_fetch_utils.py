import asyncio

import hyperbrowser.client.managers.job_fetch_utils as job_fetch_utils


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
    assert captured_kwargs["max_attempts"] == job_fetch_utils.POLLING_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == 0.5


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
    assert captured_kwargs["max_attempts"] == job_fetch_utils.POLLING_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == 0.5


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
    assert captured_kwargs["max_attempts"] == job_fetch_utils.POLLING_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == 0.5


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
    assert captured_kwargs["max_attempts"] == job_fetch_utils.POLLING_ATTEMPTS
    assert captured_kwargs["retry_delay_seconds"] == 0.5
