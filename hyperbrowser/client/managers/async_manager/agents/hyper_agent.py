from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ....polling import poll_until_terminal_status_async, retry_operation_async

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    HyperAgentTaskResponse,
    HyperAgentTaskStatusResponse,
    StartHyperAgentTaskParams,
    StartHyperAgentTaskResponse,
)


class HyperAgentManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartHyperAgentTaskParams
    ) -> StartHyperAgentTaskResponse:
        response = await self._client.transport.post(
            self._client._build_url("/task/hyper-agent"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartHyperAgentTaskResponse(**response.data)

    async def get(self, job_id: str) -> HyperAgentTaskResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/hyper-agent/{job_id}")
        )
        return HyperAgentTaskResponse(**response.data)

    async def get_status(self, job_id: str) -> HyperAgentTaskStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/hyper-agent/{job_id}/status")
        )
        return HyperAgentTaskStatusResponse(**response.data)

    async def stop(self, job_id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/task/hyper-agent/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    async def start_and_wait(
        self,
        params: StartHyperAgentTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
    ) -> HyperAgentTaskResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start HyperAgent task")

        await poll_until_terminal_status_async(
            operation_name=f"HyperAgent task {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status
            in {"completed", "failed", "stopped"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
        )
        return await retry_operation_async(
            operation_name=f"Fetching HyperAgent task {job_id}",
            operation=lambda: self.get(job_id),
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )
