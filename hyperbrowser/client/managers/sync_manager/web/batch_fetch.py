from typing import Optional

from hyperbrowser.models import (
    StartBatchFetchJobParams,
    StartBatchFetchJobResponse,
    BatchFetchJobStatusResponse,
    GetBatchFetchJobParams,
    BatchFetchJobResponse,
)
from ...page_params_utils import build_page_batch_params
from ...job_status_utils import is_default_terminal_job_status
from ...web_operation_metadata import BATCH_FETCH_OPERATION_METADATA
from ...web_route_constants import BATCH_FETCH_JOB_ROUTE_PREFIX
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
from ...job_poll_utils import (
    poll_job_until_terminal_status as poll_until_terminal_status,
)
from ...polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ...web_request_utils import get_web_job, get_web_job_status, start_web_job
from ...start_job_utils import build_started_job_context


class BatchFetchManager:
    _OPERATION_METADATA = BATCH_FETCH_OPERATION_METADATA
    _ROUTE_PREFIX = BATCH_FETCH_JOB_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    def start(self, params: StartBatchFetchJobParams) -> StartBatchFetchJobResponse:
        payload = build_batch_fetch_start_payload(params)
        return start_web_job(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=StartBatchFetchJobResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    def get_status(self, job_id: str) -> BatchFetchJobStatusResponse:
        return get_web_job_status(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=BatchFetchJobStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    def get(
        self, job_id: str, params: Optional[GetBatchFetchJobParams] = None
    ) -> BatchFetchJobResponse:
        query_params = build_batch_fetch_get_params(params)
        return get_web_job(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            params=query_params,
            model=BatchFetchJobResponse,
            operation_name=self._OPERATION_METADATA.job_operation_name,
        )

    def start_and_wait(
        self,
        params: StartBatchFetchJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> BatchFetchJobResponse:
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
