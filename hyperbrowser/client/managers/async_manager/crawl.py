from typing import Optional

from ..job_poll_utils import (
    poll_job_until_terminal_status_async as poll_until_terminal_status_async,
)
from ..job_fetch_utils import (
    collect_paginated_results_with_defaults_async,
    fetch_job_result_with_defaults_async,
    read_page_current_batch,
    read_page_total_batches,
)
from ..page_params_utils import build_page_batch_params
from ..job_pagination_utils import (
    build_job_paginated_page_merge_callback,
    initialize_job_paginated_response,
)
from ..job_status_utils import is_default_terminal_job_status
from ..job_start_payload_utils import build_crawl_start_payload
from ..polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ..serialization_utils import (
    serialize_model_dump_or_default,
)
from ..response_utils import parse_response_model
from ..start_job_utils import build_started_job_context
from ....models.crawl import (
    CrawlJobResponse,
    CrawlJobStatusResponse,
    GetCrawlJobParams,
    StartCrawlJobParams,
    StartCrawlJobResponse,
)


class CrawlManager:
    def __init__(self, client):
        self._client = client

    async def start(self, params: StartCrawlJobParams) -> StartCrawlJobResponse:
        payload = build_crawl_start_payload(params)
        response = await self._client.transport.post(
            self._client._build_url("/crawl"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartCrawlJobResponse,
            operation_name="crawl start",
        )

    async def get_status(self, job_id: str) -> CrawlJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=CrawlJobStatusResponse,
            operation_name="crawl status",
        )

    async def get(
        self, job_id: str, params: Optional[GetCrawlJobParams] = None
    ) -> CrawlJobResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=GetCrawlJobParams,
            error_message="Failed to serialize crawl get params",
        )
        response = await self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=CrawlJobResponse,
            operation_name="crawl job",
        )

    async def start_and_wait(
        self,
        params: StartCrawlJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> CrawlJobResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start crawl job",
            operation_name_prefix="crawl job ",
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

        job_response = initialize_job_paginated_response(
            model=CrawlJobResponse,
            job_id=job_id,
            status=job_status,
            total_counter_alias="totalCrawledPages",
        )

        await collect_paginated_results_with_defaults_async(
            operation_name=operation_name,
            get_next_page=lambda page: self.get(
                job_start_resp.job_id,
                params=build_page_batch_params(
                    GetCrawlJobParams,
                    page=page,
                ),
            ),
            get_current_page_batch=read_page_current_batch,
            get_total_page_batches=read_page_total_batches,
            on_page_success=build_job_paginated_page_merge_callback(
                job_response=job_response,
                total_counter_attr="total_crawled_pages",
            ),
            max_wait_seconds=max_wait_seconds,
        )

        return job_response
