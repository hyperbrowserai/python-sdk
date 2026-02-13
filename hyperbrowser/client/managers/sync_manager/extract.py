from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.consts import POLLING_ATTEMPTS
from hyperbrowser.models.extract import (
    ExtractJobResponse,
    ExtractJobStatusResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)
from ...polling import poll_until_terminal_status, retry_operation
from ...schema_utils import resolve_schema_input


class ExtractManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        if not params.schema_ and not params.prompt:
            raise HyperbrowserError("Either schema or prompt must be provided")

        payload = params.model_dump(exclude_none=True, by_alias=True)
        if params.schema_:
            payload["schema"] = resolve_schema_input(params.schema_)

        response = self._client.transport.post(
            self._client._build_url("/extract"),
            data=payload,
        )
        return StartExtractJobResponse(**response.data)

    def get_status(self, job_id: str) -> ExtractJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}/status")
        )
        return ExtractJobStatusResponse(**response.data)

    def get(self, job_id: str) -> ExtractJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}")
        )
        return ExtractJobResponse(**response.data)

    def start_and_wait(
        self,
        params: StartExtractJobParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
    ) -> ExtractJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start extract job")

        poll_until_terminal_status(
            operation_name=f"extract job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
        )
        return retry_operation(
            operation_name=f"Fetching extract job {job_id}",
            operation=lambda: self.get(job_id),
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )
