from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
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
from ..job_wait_utils import wait_for_job_result_with_defaults_async
from ..job_start_payload_utils import (
    build_batch_scrape_start_payload,
    build_scrape_start_payload,
)
from ..serialization_utils import (
    serialize_model_dump_or_default,
)
from ..response_utils import parse_response_model
from ..start_job_utils import build_started_job_context
from ....models.scrape import (
    BatchScrapeJobResponse,
    BatchScrapeJobStatusResponse,
    GetBatchScrapeJobParams,
    ScrapeJobResponse,
    ScrapeJobStatusResponse,
    StartBatchScrapeJobParams,
    StartBatchScrapeJobResponse,
    StartScrapeJobParams,
    StartScrapeJobResponse,
)


class BatchScrapeManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartBatchScrapeJobParams
    ) -> StartBatchScrapeJobResponse:
        payload = build_batch_scrape_start_payload(params)
        response = await self._client.transport.post(
            self._client._build_url("/scrape/batch"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartBatchScrapeJobResponse,
            operation_name="batch scrape start",
        )

    async def get_status(self, job_id: str) -> BatchScrapeJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=BatchScrapeJobStatusResponse,
            operation_name="batch scrape status",
        )

    async def get(
        self, job_id: str, params: Optional[GetBatchScrapeJobParams] = None
    ) -> BatchScrapeJobResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=GetBatchScrapeJobParams,
            error_message="Failed to serialize batch scrape get params",
        )
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=BatchScrapeJobResponse,
            operation_name="batch scrape job",
        )

    async def start_and_wait(
        self,
        params: StartBatchScrapeJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> BatchScrapeJobResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start batch scrape job",
            operation_name_prefix="batch scrape job ",
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
            model=BatchScrapeJobResponse,
            job_id=job_id,
            status=job_status,
            total_counter_alias="totalScrapedPages",
        )

        await collect_paginated_results_with_defaults_async(
            operation_name=operation_name,
            get_next_page=lambda page: self.get(
                job_id,
                params=build_page_batch_params(
                    GetBatchScrapeJobParams,
                    page=page,
                ),
            ),
            get_current_page_batch=read_page_current_batch,
            get_total_page_batches=read_page_total_batches,
            on_page_success=build_job_paginated_page_merge_callback(
                job_response=job_response,
                total_counter_attr="total_scraped_pages",
            ),
            max_wait_seconds=max_wait_seconds,
        )

        return job_response


class ScrapeManager:
    def __init__(self, client):
        self._client = client
        self.batch = BatchScrapeManager(client)

    async def start(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        payload = build_scrape_start_payload(params)
        response = await self._client.transport.post(
            self._client._build_url("/scrape"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartScrapeJobResponse,
            operation_name="scrape start",
        )

    async def get_status(self, job_id: str) -> ScrapeJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=ScrapeJobStatusResponse,
            operation_name="scrape status",
        )

    async def get(self, job_id: str) -> ScrapeJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=ScrapeJobResponse,
            operation_name="scrape job",
        )

    async def start_and_wait(
        self,
        params: StartScrapeJobParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> ScrapeJobResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start scrape job",
            operation_name_prefix="scrape job ",
        )

        return await wait_for_job_result_with_defaults_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_default_terminal_job_status,
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )
