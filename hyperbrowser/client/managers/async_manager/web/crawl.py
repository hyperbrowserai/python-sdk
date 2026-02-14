from typing import Optional

from hyperbrowser.models import (
    StartWebCrawlJobParams,
    StartWebCrawlJobResponse,
    WebCrawlJobStatusResponse,
    GetWebCrawlJobParams,
    WebCrawlJobResponse,
)
from ...page_params_utils import build_page_batch_params
from ...job_status_utils import is_default_terminal_job_status
from ...web_operation_metadata import WEB_CRAWL_OPERATION_METADATA
from ...web_route_constants import WEB_CRAWL_JOB_ROUTE_PREFIX
from ...web_payload_utils import build_web_crawl_start_payload
from ...web_payload_utils import build_web_crawl_get_params
from ...web_pagination_utils import (
    build_paginated_page_merge_callback,
    initialize_paginated_job_response,
)
from ...job_fetch_utils import (
    collect_paginated_results_with_defaults_async,
    fetch_job_result_with_defaults_async,
    read_page_current_batch,
    read_page_total_batches,
)
from ...job_poll_utils import (
    poll_job_until_terminal_status_async as poll_until_terminal_status_async,
)
from ...polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ...web_request_utils import (
    get_web_job_async,
    get_web_job_status_async,
    start_web_job_async,
)
from ...start_job_utils import build_started_job_context


class WebCrawlManager:
    _OPERATION_METADATA = WEB_CRAWL_OPERATION_METADATA
    _ROUTE_PREFIX = WEB_CRAWL_JOB_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    async def start(self, params: StartWebCrawlJobParams) -> StartWebCrawlJobResponse:
        payload = build_web_crawl_start_payload(params)
        return await start_web_job_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=StartWebCrawlJobResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    async def get_status(self, job_id: str) -> WebCrawlJobStatusResponse:
        return await get_web_job_status_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=WebCrawlJobStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    async def get(
        self, job_id: str, params: Optional[GetWebCrawlJobParams] = None
    ) -> WebCrawlJobResponse:
        query_params = build_web_crawl_get_params(params)
        return await get_web_job_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            params=query_params,
            model=WebCrawlJobResponse,
            operation_name=self._OPERATION_METADATA.job_operation_name,
        )

    async def start_and_wait(
        self,
        params: StartWebCrawlJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> WebCrawlJobResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message=self._OPERATION_METADATA.start_error_message,
            operation_name_prefix=self._OPERATION_METADATA.operation_name_prefix,
        )

        job_status = await poll_until_terminal_status_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_default_terminal_job_status,
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )

        if not return_all_pages:
            return await fetch_job_result_with_defaults_async(
                operation_name=operation_name,
                fetch_result=lambda: self.get(job_id),
            )

        job_response = initialize_paginated_job_response(
            model=WebCrawlJobResponse,
            job_id=job_id,
            status=job_status,
        )

        await collect_paginated_results_with_defaults_async(
            operation_name=operation_name,
            get_next_page=lambda page: self.get(
                job_id,
                params=build_page_batch_params(
                    GetWebCrawlJobParams,
                    page=page,
                ),
            ),
            get_current_page_batch=read_page_current_batch,
            get_total_page_batches=read_page_total_batches,
            on_page_success=build_paginated_page_merge_callback(
                job_response=job_response,
            ),
            max_wait_seconds=max_wait_seconds,
        )

        return job_response
