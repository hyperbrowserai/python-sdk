from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ....polling import poll_until_terminal_status, retry_operation

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    CuaTaskResponse,
    CuaTaskStatusResponse,
    StartCuaTaskParams,
    StartCuaTaskResponse,
)


class CuaManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartCuaTaskParams) -> StartCuaTaskResponse:
        response = self._client.transport.post(
            self._client._build_url("/task/cua"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartCuaTaskResponse(**response.data)

    def get(self, job_id: str) -> CuaTaskResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/cua/{job_id}")
        )
        return CuaTaskResponse(**response.data)

    def get_status(self, job_id: str) -> CuaTaskStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/cua/{job_id}/status")
        )
        return CuaTaskStatusResponse(**response.data)

    def stop(self, job_id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/task/cua/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    def start_and_wait(
        self,
        params: StartCuaTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
    ) -> CuaTaskResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start CUA task job")

        poll_until_terminal_status(
            operation_name=f"CUA task job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status
            in {"completed", "failed", "stopped"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
        )
        return retry_operation(
            operation_name=f"Fetching CUA task job {job_id}",
            operation=lambda: self.get(job_id),
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )
