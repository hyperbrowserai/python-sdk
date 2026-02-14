from typing import Optional

from hyperbrowser.models.extract import (
    ExtractJobResponse,
    ExtractJobStatusResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)
from ..extract_payload_utils import build_extract_start_payload
from ..polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ..job_wait_utils import wait_for_job_result_with_defaults
from ..job_status_utils import is_default_terminal_job_status
from ..start_job_utils import build_started_job_context
from ..response_utils import parse_response_model


class ExtractManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        payload = build_extract_start_payload(params)

        response = self._client.transport.post(
            self._client._build_url("/extract"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartExtractJobResponse,
            operation_name="extract start",
        )

    def get_status(self, job_id: str) -> ExtractJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobStatusResponse,
            operation_name="extract status",
        )

    def get(self, job_id: str) -> ExtractJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobResponse,
            operation_name="extract job",
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
            start_error_message="Failed to start extract job",
            operation_name_prefix="extract job ",
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
