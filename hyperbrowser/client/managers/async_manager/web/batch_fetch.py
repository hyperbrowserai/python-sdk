from typing import Optional

from hyperbrowser.models import (
    StartBatchFetchJobParams,
    StartBatchFetchJobResponse,
    BatchFetchJobStatusResponse,
    GetBatchFetchJobParams,
    BatchFetchJobResponse,
    POLLING_ATTEMPTS,
)
from ...page_params_utils import build_page_batch_params
from ...web_payload_utils import build_batch_fetch_start_payload
from ...web_payload_utils import build_batch_fetch_get_params
from ...web_pagination_utils import (
    build_paginated_page_merge_callback,
    initialize_paginated_job_response,
)
from ....polling import (
    build_fetch_operation_name,
    collect_paginated_results_async,
    poll_until_terminal_status_async,
    retry_operation_async,
)
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context


class BatchFetchManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartBatchFetchJobParams
    ) -> StartBatchFetchJobResponse:
        payload = build_batch_fetch_start_payload(params)

        response = await self._client.transport.post(
            self._client._build_url("/web/batch-fetch"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartBatchFetchJobResponse,
            operation_name="batch fetch start",
        )

    async def get_status(self, job_id: str) -> BatchFetchJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=BatchFetchJobStatusResponse,
            operation_name="batch fetch status",
        )

    async def get(
        self, job_id: str, params: Optional[GetBatchFetchJobParams] = None
    ) -> BatchFetchJobResponse:
        query_params = build_batch_fetch_get_params(params)
        response = await self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=BatchFetchJobResponse,
            operation_name="batch fetch job",
        )

    async def start_and_wait(
        self,
        params: StartBatchFetchJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> BatchFetchJobResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start batch fetch job",
            operation_name_prefix="batch fetch job ",
        )

        job_status = await poll_until_terminal_status_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )

        if not return_all_pages:
            return await retry_operation_async(
                operation_name=build_fetch_operation_name(operation_name),
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        job_response = initialize_paginated_job_response(
            model=BatchFetchJobResponse,
            job_id=job_id,
            status=job_status,
        )

        await collect_paginated_results_async(
            operation_name=operation_name,
            get_next_page=lambda page: self.get(
                job_id,
                params=build_page_batch_params(
                    GetBatchFetchJobParams,
                    page=page,
                ),
            ),
            get_current_page_batch=lambda page_response: (
                page_response.current_page_batch
            ),
            get_total_page_batches=lambda page_response: (
                page_response.total_page_batches
            ),
            on_page_success=build_paginated_page_merge_callback(
                job_response=job_response,
            ),
            max_wait_seconds=max_wait_seconds,
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )

        return job_response
