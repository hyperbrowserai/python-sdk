from typing import Optional

from ...agent_payload_utils import build_agent_start_payload
from ...agent_status_utils import is_agent_terminal_status
from ...agent_stop_utils import stop_agent_task_async
from ...job_wait_utils import wait_for_job_result_with_defaults_async
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context

from .....models import (
    BasicResponse,
    HyperAgentTaskResponse,
    HyperAgentTaskStatusResponse,
    StartHyperAgentTaskParams,
    StartHyperAgentTaskResponse,
)
from ...polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)


class HyperAgentManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartHyperAgentTaskParams
    ) -> StartHyperAgentTaskResponse:
        payload = build_agent_start_payload(
            params,
            error_message="Failed to serialize HyperAgent start params",
        )
        response = await self._client.transport.post(
            self._client._build_url("/task/hyper-agent"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartHyperAgentTaskResponse,
            operation_name="hyper agent start",
        )

    async def get(self, job_id: str) -> HyperAgentTaskResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/hyper-agent/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=HyperAgentTaskResponse,
            operation_name="hyper agent task",
        )

    async def get_status(self, job_id: str) -> HyperAgentTaskStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/hyper-agent/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=HyperAgentTaskStatusResponse,
            operation_name="hyper agent task status",
        )

    async def stop(self, job_id: str) -> BasicResponse:
        return await stop_agent_task_async(
            client=self._client,
            route_prefix="/task/hyper-agent",
            job_id=job_id,
            operation_name="hyper agent task stop",
        )

    async def start_and_wait(
        self,
        params: StartHyperAgentTaskParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> HyperAgentTaskResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start HyperAgent task",
            operation_name_prefix="HyperAgent task ",
        )

        return await wait_for_job_result_with_defaults_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_agent_terminal_status,
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )
