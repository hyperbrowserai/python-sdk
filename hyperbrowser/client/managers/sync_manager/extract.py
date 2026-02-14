from typing import Optional

from hyperbrowser.models.extract import (
    ExtractJobResponse,
    ExtractJobStatusResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)
from ..extract_payload_utils import build_extract_start_payload
from ..job_operation_metadata import EXTRACT_OPERATION_METADATA
from ..job_request_utils import get_job, get_job_status, start_job
from ..job_route_constants import EXTRACT_JOB_ROUTE_PREFIX
from ..polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ..job_wait_utils import wait_for_job_result_with_defaults
from ..job_status_utils import is_default_terminal_job_status
from ..start_job_utils import build_started_job_context


class ExtractManager:
    _OPERATION_METADATA = EXTRACT_OPERATION_METADATA
    _ROUTE_PREFIX = EXTRACT_JOB_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        payload = build_extract_start_payload(params)
        return start_job(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=StartExtractJobResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    def get_status(self, job_id: str) -> ExtractJobStatusResponse:
        return get_job_status(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=ExtractJobStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    def get(self, job_id: str) -> ExtractJobResponse:
        return get_job(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            params=None,
            model=ExtractJobResponse,
            operation_name=self._OPERATION_METADATA.job_operation_name,
        )

    def start_and_wait(
        self,
        params: StartExtractJobParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> ExtractJobResponse:
        job_start_resp = self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message=self._OPERATION_METADATA.start_error_message,
            operation_name_prefix=self._OPERATION_METADATA.operation_name_prefix,
        )

        return wait_for_job_result_with_defaults(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_default_terminal_job_status,
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )
