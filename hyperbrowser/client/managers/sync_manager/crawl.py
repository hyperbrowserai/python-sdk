from typing import Optional

from ..job_poll_utils import poll_job_until_terminal_status as poll_until_terminal_status
from ..job_fetch_utils import (
    collect_paginated_results_with_defaults,
    fetch_job_result_with_defaults,
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
from ..job_operation_metadata import CRAWL_OPERATION_METADATA
from ..job_request_utils import get_job, get_job_status, start_job
from ..job_route_constants import CRAWL_JOB_ROUTE_PREFIX
from ..job_query_params_utils import build_crawl_get_params
from ..polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ..start_job_utils import build_started_job_context
from ....models.crawl import (
    CrawlJobResponse,
    CrawlJobStatusResponse,
    GetCrawlJobParams,
    StartCrawlJobParams,
    StartCrawlJobResponse,
)


class CrawlManager:
    _OPERATION_METADATA = CRAWL_OPERATION_METADATA
    _ROUTE_PREFIX = CRAWL_JOB_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    def start(self, params: StartCrawlJobParams) -> StartCrawlJobResponse:
        payload = build_crawl_start_payload(params)
        return start_job(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=StartCrawlJobResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    def get_status(self, job_id: str) -> CrawlJobStatusResponse:
        return get_job_status(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=CrawlJobStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    def get(
        self, job_id: str, params: Optional[GetCrawlJobParams] = None
    ) -> CrawlJobResponse:
        query_params = build_crawl_get_params(params)
        return get_job(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            params=query_params,
            model=CrawlJobResponse,
            operation_name=self._OPERATION_METADATA.job_operation_name,
        )

    def start_and_wait(
        self,
        params: StartCrawlJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> CrawlJobResponse:
        job_start_resp = self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message=self._OPERATION_METADATA.start_error_message,
            operation_name_prefix=self._OPERATION_METADATA.operation_name_prefix,
        )

        job_status = poll_until_terminal_status(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_default_terminal_job_status,
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )

        if not return_all_pages:
            return fetch_job_result_with_defaults(
                operation_name=operation_name,
                fetch_result=lambda: self.get(job_id),
            )

        job_response = initialize_job_paginated_response(
            model=CrawlJobResponse,
            job_id=job_id,
            status=job_status,
            total_counter_alias="totalCrawledPages",
        )

        collect_paginated_results_with_defaults(
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
