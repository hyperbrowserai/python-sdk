from typing import Optional

from ....polling import wait_for_job_result
from ...agent_payload_utils import build_agent_start_payload
from ...agent_status_utils import is_agent_terminal_status
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context

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

    def start(
        self, params: StartClaudeComputerUseTaskParams
    ) -> StartClaudeComputerUseTaskResponse:
        payload = build_agent_start_payload(
            params,
            error_message="Failed to serialize Claude Computer Use start params",
        )
        response = self._client.transport.post(
            self._client._build_url("/task/claude-computer-use"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartClaudeComputerUseTaskResponse,
            operation_name="claude computer use start",
        )

    def get(self, job_id: str) -> ClaudeComputerUseTaskResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/claude-computer-use/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=ClaudeComputerUseTaskResponse,
            operation_name="claude computer use task",
        )

    def get_status(self, job_id: str) -> ClaudeComputerUseTaskStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/claude-computer-use/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=ClaudeComputerUseTaskStatusResponse,
            operation_name="claude computer use task status",
        )

    def stop(self, job_id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/task/claude-computer-use/{job_id}/stop")
        )
        return parse_response_model(
            response.data,
            model=BasicResponse,
            operation_name="claude computer use task stop",
        )

    def start_and_wait(
        self,
        params: StartClaudeComputerUseTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> ClaudeComputerUseTaskResponse:
        job_start_resp = self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start Claude Computer Use task job",
            operation_name_prefix="Claude Computer Use task job ",
        )

        return wait_for_job_result(
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
