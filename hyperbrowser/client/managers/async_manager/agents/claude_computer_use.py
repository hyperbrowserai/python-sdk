from typing import Optional

from ...agent_payload_utils import build_agent_start_payload
from ...agent_operation_metadata import CLAUDE_COMPUTER_USE_OPERATION_METADATA
from ...agent_route_constants import CLAUDE_COMPUTER_USE_TASK_ROUTE_PREFIX
from ...agent_status_utils import is_agent_terminal_status
from ...agent_stop_utils import stop_agent_task_async
from ...agent_task_read_utils import get_agent_task_async, get_agent_task_status_async
from ...job_wait_utils import wait_for_job_result_with_defaults_async
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context

from .....models import (
    BasicResponse,
    ClaudeComputerUseTaskResponse,
    ClaudeComputerUseTaskStatusResponse,
    StartClaudeComputerUseTaskParams,
    StartClaudeComputerUseTaskResponse,
)
from ...polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)


class ClaudeComputerUseManager:
    _OPERATION_METADATA = CLAUDE_COMPUTER_USE_OPERATION_METADATA
    _ROUTE_PREFIX = CLAUDE_COMPUTER_USE_TASK_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartClaudeComputerUseTaskParams
    ) -> StartClaudeComputerUseTaskResponse:
        payload = build_agent_start_payload(
            params,
            error_message="Failed to serialize Claude Computer Use start params",
        )
        response = await self._client.transport.post(
            self._client._build_url(self._ROUTE_PREFIX),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartClaudeComputerUseTaskResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    async def get(self, job_id: str) -> ClaudeComputerUseTaskResponse:
        return await get_agent_task_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=ClaudeComputerUseTaskResponse,
            operation_name=self._OPERATION_METADATA.task_operation_name,
        )

    async def get_status(self, job_id: str) -> ClaudeComputerUseTaskStatusResponse:
        return await get_agent_task_status_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=ClaudeComputerUseTaskStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    async def stop(self, job_id: str) -> BasicResponse:
        return await stop_agent_task_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            operation_name=self._OPERATION_METADATA.stop_operation_name,
        )

    async def start_and_wait(
        self,
        params: StartClaudeComputerUseTaskParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> ClaudeComputerUseTaskResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message=self._OPERATION_METADATA.start_error_message,
            operation_name_prefix=self._OPERATION_METADATA.operation_name_prefix,
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
