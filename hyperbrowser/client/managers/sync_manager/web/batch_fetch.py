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
from ...job_status_utils import is_default_terminal_job_status
from ...web_payload_utils import build_batch_fetch_start_payload
from ...web_payload_utils import build_batch_fetch_get_params
from ...web_pagination_utils import (
    build_paginated_page_merge_callback,
    initialize_paginated_job_response,
)
from ...job_fetch_utils import (
    collect_paginated_results_with_defaults,
    fetch_job_result_with_defaults,
    read_page_current_batch,
    read_page_total_batches,
)
from ....polling import (
    poll_until_terminal_status,
)
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context


class BatchFetchManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartBatchFetchJobParams) -> StartBatchFetchJobResponse:
        payload = build_batch_fetch_start_payload(params)

        response = self._client.transport.post(
            self._client._build_url("/web/batch-fetch"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartBatchFetchJobResponse,
            operation_name="batch fetch start",
        )

    def get_status(self, job_id: str) -> BatchFetchJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=BatchFetchJobStatusResponse,
            operation_name="batch fetch status",
        )

    def get(
        self, job_id: str, params: Optional[GetBatchFetchJobParams] = None
    ) -> BatchFetchJobResponse:
        query_params = build_batch_fetch_get_params(params)
        response = self._client.transport.get(
            self._client._build_url(f"/web/batch-fetch/{job_id}"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=BatchFetchJobResponse,
            operation_name="batch fetch job",
        )

    def start_and_wait(
        self,
        params: StartBatchFetchJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> BatchFetchJobResponse:
        job_start_resp = self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start batch fetch job",
            operation_name_prefix="batch fetch job ",
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

        job_response = initialize_paginated_job_response(
            model=BatchFetchJobResponse,
            job_id=job_id,
            status=job_status,
        )

        collect_paginated_results_with_defaults(
            operation_name=operation_name,
            get_next_page=lambda page: self.get(
                job_id,
                params=build_page_batch_params(
                    GetBatchFetchJobParams,
                    page=page,
                ),
            ),
            get_current_page_batch=read_page_current_batch,
            get_total_page_batches=read_page_total_batches,
            on_page_success=build_paginated_page_merge_callback(
                job_response=job_response,
            ),
            max_wait_seconds=max_wait_seconds,
        )

        return job_response
