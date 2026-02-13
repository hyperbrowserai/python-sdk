from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ....polling import poll_until_terminal_status_async, retry_operation_async

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

    async def start(self, params: StartCuaTaskParams) -> StartCuaTaskResponse:
        response = await self._client.transport.post(
            self._client._build_url("/task/cua"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartCuaTaskResponse(**response.data)

    async def get(self, job_id: str) -> CuaTaskResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/cua/{job_id}")
        )
        return CuaTaskResponse(**response.data)

    async def get_status(self, job_id: str) -> CuaTaskStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/cua/{job_id}/status")
        )
        return CuaTaskStatusResponse(**response.data)

    async def stop(self, job_id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/task/cua/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    async def start_and_wait(
        self,
        params: StartCuaTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> CuaTaskResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start CUA task job")

        await poll_until_terminal_status_async(
            operation_name=f"CUA task job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status
            in {"completed", "failed", "stopped"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )
        return await retry_operation_async(
            operation_name=f"Fetching CUA task job {job_id}",
            operation=lambda: self.get(job_id),
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )
