from hyperbrowser.models import (
    StartWebCrawlJobParams,
    StartWebCrawlJobResponse,
    WebCrawlJobStatusResponse,
    GetWebCrawlJobParams,
    WebCrawlJobResponse,
    WebCrawlJobStatus,
    POLLING_ATTEMPTS,
    FetchOutputJson,
)
from hyperbrowser.models.params import (
    coerce_to_model,
    GetWebCrawlJobParamsDict,
    StartWebCrawlJobParamsDict,
)
from hyperbrowser.exceptions import HyperbrowserError
from typing import Union
import time
import jsonref


class WebCrawlManager:
    def __init__(self, client):
        self._client = client

    def start(
        self, params: Union[StartWebCrawlJobParams, StartWebCrawlJobParamsDict]
    ) -> StartWebCrawlJobResponse:
        params = coerce_to_model(StartWebCrawlJobParams, params)
        if params.outputs and params.outputs.formats:
            for output in params.outputs.formats:
                if isinstance(output, FetchOutputJson) and output.schema_:
                    if hasattr(output.schema_, "model_json_schema"):
                        output.schema_ = jsonref.replace_refs(
                            output.schema_.model_json_schema(),
                            proxies=False,
                            lazy_load=False,
                        )

        response = self._client.transport.post(
            self._client._build_url("/web/crawl"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartWebCrawlJobResponse(**response.data)

    def get_status(self, job_id: str) -> WebCrawlJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}/status")
        )
        return WebCrawlJobStatusResponse(**response.data)

    def get(
        self,
        job_id: str,
        params: Union[
            GetWebCrawlJobParams, GetWebCrawlJobParamsDict
        ] = GetWebCrawlJobParams(),
    ) -> WebCrawlJobResponse:
        params = coerce_to_model(GetWebCrawlJobParams, params)
        response = self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return WebCrawlJobResponse(**response.data)

    def start_and_wait(
        self,
        params: Union[StartWebCrawlJobParams, StartWebCrawlJobParamsDict],
        return_all_pages: bool = True,
    ) -> WebCrawlJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start web crawl job")

        job_status: WebCrawlJobStatus = "pending"
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
                        f"Failed to poll web crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
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
                            f"Failed to get web crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                        )
                time.sleep(0.5)

        failures = 0
        job_response = WebCrawlJobResponse(
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
                    params=GetWebCrawlJobParams(
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
                        f"Failed to get batch page {job_response.current_page_batch} for web crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(0.5)

        return job_response
