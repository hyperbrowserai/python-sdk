from typing import Optional

from hyperbrowser.models import (
    StartBatchFetchJobParams,
    StartBatchFetchJobResponse,
    BatchFetchJobStatusResponse,
    GetBatchFetchJobParams,
    BatchFetchJobResponse,
    POLLING_ATTEMPTS,
    FetchOutputJson,
)
from hyperbrowser.exceptions import HyperbrowserError
from ....polling import (
    has_exceeded_max_wait,
    poll_until_terminal_status_async,
    retry_operation_async,
)
import asyncio
import time
import jsonref


class BatchFetchManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartBatchFetchJobParams
    ) -> StartBatchFetchJobResponse:
        payload = params.model_dump(exclude_none=True, by_alias=True)
        if params.outputs and params.outputs.formats:
            for index, output in enumerate(params.outputs.formats):
                if isinstance(output, FetchOutputJson) and output.schema_:
                    if hasattr(output.schema_, "model_json_schema"):
                        payload["outputs"]["formats"][index]["schema"] = jsonref.replace_refs(
                            output.schema_.model_json_schema(),
                            proxies=False,
                            lazy_load=False,
                        )

        response = await self._client.transport.post(
            self._client._build_url("/web/batch-fetch"),
            data=payload,
        )
        return StartBatchFetchJobResponse(**response.data)

    async def get_status(self, job_id: str) -> BatchFetchJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}/status")
        )
        return BatchFetchJobStatusResponse(**response.data)

    async def get(
        self, job_id: str, params: Optional[GetBatchFetchJobParams] = None
    ) -> BatchFetchJobResponse:
        params_obj = params or GetBatchFetchJobParams()
        response = await self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return BatchFetchJobResponse(**response.data)

    async def start_and_wait(
        self,
        params: StartBatchFetchJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
    ) -> BatchFetchJobResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start batch fetch job")

        job_status = await poll_until_terminal_status_async(
            operation_name=f"batch fetch job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
        )

        if not return_all_pages:
            return await retry_operation_async(
                operation_name=f"Fetching batch fetch job {job_id}",
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        failures = 0
        page_fetch_start_time = time.monotonic()
        job_response = BatchFetchJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalPages=0,
            batchSize=100,
        )
        first_check = True

        while (
            first_check
            or job_response.current_page_batch < job_response.total_page_batches
        ):
            if has_exceeded_max_wait(page_fetch_start_time, max_wait_seconds):
                raise HyperbrowserError(
                    f"Timed out fetching all pages for batch fetch job {job_id} after {max_wait_seconds} seconds"
                )
            try:
                tmp_job_response = await self.get(
                    job_id,
                    params=GetBatchFetchJobParams(
                        page=job_response.current_page_batch + 1, batch_size=100
                    ),
                )
                if tmp_job_response.data:
                    job_response.data.extend(tmp_job_response.data)
                job_response.current_page_batch = tmp_job_response.current_page_batch
                job_response.total_pages = tmp_job_response.total_pages
                job_response.total_page_batches = tmp_job_response.total_page_batches
                job_response.batch_size = tmp_job_response.batch_size
                job_response.error = tmp_job_response.error
                failures = 0
                first_check = False
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to get batch page {job_response.current_page_batch} for job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            await asyncio.sleep(0.5)

        return job_response
