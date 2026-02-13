from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ....polling import build_operation_name, wait_for_job_result
from ....schema_utils import resolve_schema_input

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    BrowserUseTaskResponse,
    BrowserUseTaskStatusResponse,
    StartBrowserUseTaskParams,
    StartBrowserUseTaskResponse,
)


class BrowserUseManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartBrowserUseTaskParams) -> StartBrowserUseTaskResponse:
        payload = params.model_dump(exclude_none=True, by_alias=True)
        if params.output_model_schema:
            payload["outputModelSchema"] = resolve_schema_input(
                params.output_model_schema
            )
        response = self._client.transport.post(
            self._client._build_url("/task/browser-use"),
            data=payload,
        )
        return StartBrowserUseTaskResponse(**response.data)

    def get(self, job_id: str) -> BrowserUseTaskResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/browser-use/{job_id}")
        )
        return BrowserUseTaskResponse(**response.data)

    def get_status(self, job_id: str) -> BrowserUseTaskStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/browser-use/{job_id}/status")
        )
        return BrowserUseTaskStatusResponse(**response.data)

    def stop(self, job_id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/task/browser-use/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    def start_and_wait(
        self,
        params: StartBrowserUseTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> BrowserUseTaskResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start browser-use task job")
        operation_name = build_operation_name("browser-use task job ", job_id)

        return wait_for_job_result(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: (
                status in {"completed", "failed", "stopped"}
            ),
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
            fetch_max_attempts=POLLING_ATTEMPTS,
            fetch_retry_delay_seconds=0.5,
        )
