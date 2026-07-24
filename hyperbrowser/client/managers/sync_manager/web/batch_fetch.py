import time
from typing import Optional, Union

from hyperbrowser.client._request import (
    dump_request,
    dump_request_with_fetch_schemas,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    StartBatchFetchJobParams,
    StartBatchFetchJobResponse,
    BatchFetchJobStatusResponse,
    GetBatchFetchJobParams,
    BatchFetchJobResponse,
    BatchFetchJobStatus,
    POLLING_ATTEMPTS,
)
from hyperbrowser.types import (
    GetBatchFetchJobParams as GetBatchFetchJobParamsDict,
    StartBatchFetchJobParams as StartBatchFetchJobParamsDict,
)


class BatchFetchManager:
    def __init__(self, client):
        self._client = client

    def start(
        self,
        params: Union[StartBatchFetchJobParamsDict, StartBatchFetchJobParams],
    ) -> StartBatchFetchJobResponse:
        response = self._client.transport.post(
            self._client._build_url("/web/batch-fetch"),
            data=dump_request_with_fetch_schemas(params, StartBatchFetchJobParams),
        )
        return StartBatchFetchJobResponse(**response.data)

    def get_status(self, job_id: str) -> BatchFetchJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}/status")
        )
        return BatchFetchJobStatusResponse(**response.data)

    def get(
        self,
        job_id: str,
        params: Optional[
            Union[GetBatchFetchJobParamsDict, GetBatchFetchJobParams]
        ] = None,
    ) -> BatchFetchJobResponse:
        if params is None:
            params = GetBatchFetchJobParams()
        response = self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}"),
            params=dump_request(params, GetBatchFetchJobParams),
        )
        return BatchFetchJobResponse(**response.data)

    def start_and_wait(
        self,
        params: Union[StartBatchFetchJobParamsDict, StartBatchFetchJobParams],
        return_all_pages: bool = True,
    ) -> BatchFetchJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start batch fetch job")

        job_status: BatchFetchJobStatus = "pending"
        failures = 0
        while True:
            try:
                job_status_resp = self.get_status(job_id)
                job_status = job_status_resp.status
                if job_status == "completed" or job_status == "failed":
                    break
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll batch fetch job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(2)

        failures = 0
        if not return_all_pages:
            while True:
                try:
                    return self.get(job_id)
                except Exception as e:
                    failures += 1
                    if failures >= POLLING_ATTEMPTS:
                        raise HyperbrowserError(
                            f"Failed to get batch fetch job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                        )
                time.sleep(0.5)

        failures = 0
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
            try:
                tmp_job_response = self.get(
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
            time.sleep(0.5)

        return job_response
