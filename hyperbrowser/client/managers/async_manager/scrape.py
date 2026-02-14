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
from ..job_wait_utils import wait_for_job_result_with_defaults_async
from ..job_operation_metadata import (
    BATCH_SCRAPE_OPERATION_METADATA,
    SCRAPE_OPERATION_METADATA,
)
from ..job_request_utils import get_job_async, get_job_status_async, start_job_async
from ..job_route_constants import (
    BATCH_SCRAPE_JOB_ROUTE_PREFIX,
    SCRAPE_JOB_ROUTE_PREFIX,
)
from ..job_query_params_utils import build_batch_scrape_get_params
from ..polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ..job_start_payload_utils import (
    build_batch_scrape_start_payload,
    build_scrape_start_payload,
)
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
    _OPERATION_METADATA = BATCH_SCRAPE_OPERATION_METADATA
    _ROUTE_PREFIX = BATCH_SCRAPE_JOB_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartBatchScrapeJobParams
    ) -> StartBatchScrapeJobResponse:
        payload = build_batch_scrape_start_payload(params)
        return await start_job_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=StartBatchScrapeJobResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    async def get_status(self, job_id: str) -> BatchScrapeJobStatusResponse:
        return await get_job_status_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=BatchScrapeJobStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    async def get(
        self, job_id: str, params: Optional[GetBatchScrapeJobParams] = None
    ) -> BatchScrapeJobResponse:
        query_params = build_batch_scrape_get_params(params)
        return await get_job_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            params=query_params,
            model=BatchScrapeJobResponse,
            operation_name=self._OPERATION_METADATA.job_operation_name,
        )

    async def start_and_wait(
        self,
        params: StartBatchScrapeJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> BatchScrapeJobResponse:
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
    _OPERATION_METADATA = SCRAPE_OPERATION_METADATA
    _ROUTE_PREFIX = SCRAPE_JOB_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client
        self.batch = BatchScrapeManager(client)

    async def start(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        payload = build_scrape_start_payload(params)
        return await start_job_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=StartScrapeJobResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    async def get_status(self, job_id: str) -> ScrapeJobStatusResponse:
        return await get_job_status_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=ScrapeJobStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    async def get(self, job_id: str) -> ScrapeJobResponse:
        return await get_job_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            params=None,
            model=ScrapeJobResponse,
            operation_name=self._OPERATION_METADATA.job_operation_name,
        )

    async def start_and_wait(
        self,
        params: StartScrapeJobParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> ScrapeJobResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message=self._OPERATION_METADATA.start_error_message,
            operation_name_prefix=self._OPERATION_METADATA.operation_name_prefix,
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
