from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ....polling import poll_until_terminal_status_async, retry_operation_async
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

    async def start(
        self, params: StartBrowserUseTaskParams
    ) -> StartBrowserUseTaskResponse:
        payload = params.model_dump(exclude_none=True, by_alias=True)
        if params.output_model_schema:
            payload["outputModelSchema"] = resolve_schema_input(
                params.output_model_schema
            )
        response = await self._client.transport.post(
            self._client._build_url("/task/browser-use"),
            data=payload,
        )
        return StartBrowserUseTaskResponse(**response.data)

    async def get(self, job_id: str) -> BrowserUseTaskResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/browser-use/{job_id}")
        )
        return BrowserUseTaskResponse(**response.data)

    async def get_status(self, job_id: str) -> BrowserUseTaskStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/browser-use/{job_id}/status")
        )
        return BrowserUseTaskStatusResponse(**response.data)

    async def stop(self, job_id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/task/browser-use/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    async def start_and_wait(
        self,
        params: StartBrowserUseTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> BrowserUseTaskResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start browser-use task job")

        await poll_until_terminal_status_async(
            operation_name=f"browser-use task job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status
            in {"completed", "failed", "stopped"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )
        return await retry_operation_async(
            operation_name=f"Fetching browser-use task job {job_id}",
            operation=lambda: self.get(job_id),
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )
