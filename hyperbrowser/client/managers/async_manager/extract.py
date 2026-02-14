from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
from hyperbrowser.models.extract import (
    ExtractJobResponse,
    ExtractJobStatusResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)
from ...polling import (
    build_operation_name,
    ensure_started_job_id,
    wait_for_job_result_async,
)
from ..extract_payload_utils import build_extract_start_payload
from ..response_utils import parse_response_model


class ExtractManager:
    def __init__(self, client):
        self._client = client

    async def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        payload = build_extract_start_payload(params)

        response = await self._client.transport.post(
            self._client._build_url("/extract"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartExtractJobResponse,
            operation_name="extract start",
        )

    async def get_status(self, job_id: str) -> ExtractJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobStatusResponse,
            operation_name="extract status",
        )

    async def get(self, job_id: str) -> ExtractJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobResponse,
            operation_name="extract job",
        )

    async def start_and_wait(
        self,
        params: StartExtractJobParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> ExtractJobResponse:
        job_start_resp = await self.start(params)
        job_id = ensure_started_job_id(
            job_start_resp.job_id,
            error_message="Failed to start extract job",
        )
        operation_name = build_operation_name("extract job ", job_id)

        return await wait_for_job_result_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
            fetch_max_attempts=POLLING_ATTEMPTS,
            fetch_retry_delay_seconds=0.5,
        )
