from typing import Optional

from ....polling import wait_for_job_result_async
from ...agent_payload_utils import build_agent_start_payload
from ...agent_status_utils import is_agent_terminal_status
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    GeminiComputerUseTaskResponse,
    GeminiComputerUseTaskStatusResponse,
    StartGeminiComputerUseTaskParams,
    StartGeminiComputerUseTaskResponse,
)


class GeminiComputerUseManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartGeminiComputerUseTaskParams
    ) -> StartGeminiComputerUseTaskResponse:
        payload = build_agent_start_payload(
            params,
            error_message="Failed to serialize Gemini Computer Use start params",
        )
        response = await self._client.transport.post(
            self._client._build_url("/task/gemini-computer-use"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartGeminiComputerUseTaskResponse,
            operation_name="gemini computer use start",
        )

    async def get(self, job_id: str) -> GeminiComputerUseTaskResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/gemini-computer-use/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=GeminiComputerUseTaskResponse,
            operation_name="gemini computer use task",
        )

    async def get_status(self, job_id: str) -> GeminiComputerUseTaskStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/gemini-computer-use/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=GeminiComputerUseTaskStatusResponse,
            operation_name="gemini computer use task status",
        )

    async def stop(self, job_id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/task/gemini-computer-use/{job_id}/stop")
        )
        return parse_response_model(
            response.data,
            model=BasicResponse,
            operation_name="gemini computer use task stop",
        )

    async def start_and_wait(
        self,
        params: StartGeminiComputerUseTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> GeminiComputerUseTaskResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start Gemini Computer Use task job",
            operation_name_prefix="Gemini Computer Use task job ",
        )

        return await wait_for_job_result_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_agent_terminal_status,
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
            fetch_max_attempts=POLLING_ATTEMPTS,
            fetch_retry_delay_seconds=0.5,
        )
