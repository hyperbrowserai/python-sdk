from typing import Optional

from hyperbrowser.models import (
    StartWebCrawlJobParams,
    StartWebCrawlJobResponse,
    WebCrawlJobStatusResponse,
    GetWebCrawlJobParams,
    WebCrawlJobResponse,
    POLLING_ATTEMPTS,
)
from ...web_payload_utils import build_web_crawl_start_payload
from ...web_payload_utils import build_web_crawl_get_params
from ...web_pagination_utils import (
    initialize_paginated_job_response,
    merge_paginated_page_response,
)
from ....polling import (
    build_fetch_operation_name,
    build_operation_name,
    collect_paginated_results,
    ensure_started_job_id,
    poll_until_terminal_status,
    retry_operation,
)
from ...response_utils import parse_response_model


class WebCrawlManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartWebCrawlJobParams) -> StartWebCrawlJobResponse:
        payload = build_web_crawl_start_payload(params)

        response = self._client.transport.post(
            self._client._build_url("/web/crawl"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartWebCrawlJobResponse,
            operation_name="web crawl start",
        )

    def get_status(self, job_id: str) -> WebCrawlJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=WebCrawlJobStatusResponse,
            operation_name="web crawl status",
        )

    def get(
        self, job_id: str, params: Optional[GetWebCrawlJobParams] = None
    ) -> WebCrawlJobResponse:
        query_params = build_web_crawl_get_params(params)
        response = self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=WebCrawlJobResponse,
            operation_name="web crawl job",
        )

    def start_and_wait(
        self,
        params: StartWebCrawlJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> WebCrawlJobResponse:
        job_start_resp = self.start(params)
        job_id = ensure_started_job_id(
            job_start_resp.job_id,
            error_message="Failed to start web crawl job",
        )
        operation_name = build_operation_name("web crawl job ", job_id)

        job_status = poll_until_terminal_status(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )

        if not return_all_pages:
            return retry_operation(
                operation_name=build_fetch_operation_name(operation_name),
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        job_response = initialize_paginated_job_response(
            model=WebCrawlJobResponse,
            job_id=job_id,
            status=job_status,
        )

        def merge_page_response(page_response: WebCrawlJobResponse) -> None:
            merge_paginated_page_response(job_response, page_response)

        collect_paginated_results(
            operation_name=operation_name,
            get_next_page=lambda page: self.get(
                job_id,
                params=GetWebCrawlJobParams(page=page, batch_size=100),
            ),
            get_current_page_batch=lambda page_response: (
                page_response.current_page_batch
            ),
            get_total_page_batches=lambda page_response: (
                page_response.total_page_batches
            ),
            on_page_success=merge_page_response,
            max_wait_seconds=max_wait_seconds,
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )

        return job_response
