from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ....polling import wait_for_job_result_async

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    ClaudeComputerUseTaskResponse,
    ClaudeComputerUseTaskStatusResponse,
    StartClaudeComputerUseTaskParams,
    StartClaudeComputerUseTaskResponse,
)


class ClaudeComputerUseManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartClaudeComputerUseTaskParams
    ) -> StartClaudeComputerUseTaskResponse:
        response = await self._client.transport.post(
            self._client._build_url("/task/claude-computer-use"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartClaudeComputerUseTaskResponse(**response.data)

    async def get(self, job_id: str) -> ClaudeComputerUseTaskResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/claude-computer-use/{job_id}")
        )
        return ClaudeComputerUseTaskResponse(**response.data)

    async def get_status(self, job_id: str) -> ClaudeComputerUseTaskStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/claude-computer-use/{job_id}/status")
        )
        return ClaudeComputerUseTaskStatusResponse(**response.data)

    async def stop(self, job_id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/task/claude-computer-use/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    async def start_and_wait(
        self,
        params: StartClaudeComputerUseTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> ClaudeComputerUseTaskResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start Claude Computer Use task job")

        return await wait_for_job_result_async(
            operation_name=f"Claude Computer Use task job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status
            in {"completed", "failed", "stopped"},
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
            fetch_max_attempts=POLLING_ATTEMPTS,
            fetch_retry_delay_seconds=0.5,
        )
