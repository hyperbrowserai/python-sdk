from typing import Optional

from hyperbrowser.models import (
    StartBatchFetchJobParams,
    StartBatchFetchJobResponse,
    BatchFetchJobStatusResponse,
    GetBatchFetchJobParams,
    BatchFetchJobResponse,
    POLLING_ATTEMPTS,
)
from hyperbrowser.exceptions import HyperbrowserError
from ....polling import (
    collect_paginated_results,
    poll_until_terminal_status,
    retry_operation,
)
from ....schema_utils import inject_web_output_schemas


class BatchFetchManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartBatchFetchJobParams) -> StartBatchFetchJobResponse:
        payload = params.model_dump(exclude_none=True, by_alias=True)
        inject_web_output_schemas(
            payload, params.outputs.formats if params.outputs else None
        )

        response = self._client.transport.post(
            self._client._build_url("/web/batch-fetch"),
            data=payload,
        )
        return StartBatchFetchJobResponse(**response.data)

    def get_status(self, job_id: str) -> BatchFetchJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}/status")
        )
        return BatchFetchJobStatusResponse(**response.data)

    def get(
        self, job_id: str, params: Optional[GetBatchFetchJobParams] = None
    ) -> BatchFetchJobResponse:
        params_obj = params or GetBatchFetchJobParams()
        response = self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return BatchFetchJobResponse(**response.data)

    def start_and_wait(
        self,
        params: StartBatchFetchJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
    ) -> BatchFetchJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start batch fetch job")

        job_status = poll_until_terminal_status(
            operation_name=f"batch fetch job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
        )

        if not return_all_pages:
            return retry_operation(
                operation_name=f"Fetching batch fetch job {job_id}",
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        job_response = BatchFetchJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalPages=0,
            batchSize=100,
        )

        def merge_page_response(page_response: BatchFetchJobResponse) -> None:
            if page_response.data:
                job_response.data.extend(page_response.data)
            job_response.current_page_batch = page_response.current_page_batch
            job_response.total_pages = page_response.total_pages
            job_response.total_page_batches = page_response.total_page_batches
            job_response.batch_size = page_response.batch_size
            job_response.error = page_response.error

        collect_paginated_results(
            operation_name=f"batch fetch job {job_id}",
            get_next_page=lambda page: self.get(
                job_id,
                params=GetBatchFetchJobParams(page=page, batch_size=100),
            ),
            get_current_page_batch=lambda page_response: page_response.current_page_batch,
            get_total_page_batches=lambda page_response: page_response.total_page_batches,
            on_page_success=merge_page_response,
            max_wait_seconds=max_wait_seconds,
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )

        return job_response
