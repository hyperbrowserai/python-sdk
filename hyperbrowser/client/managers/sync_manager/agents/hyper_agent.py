from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ....polling import build_operation_name, wait_for_job_result

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

    def start(self, params: StartHyperAgentTaskParams) -> StartHyperAgentTaskResponse:
        response = self._client.transport.post(
            self._client._build_url("/task/hyper-agent"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartHyperAgentTaskResponse(**response.data)

    def get(self, job_id: str) -> HyperAgentTaskResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/hyper-agent/{job_id}")
        )
        return HyperAgentTaskResponse(**response.data)

    def get_status(self, job_id: str) -> HyperAgentTaskStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/hyper-agent/{job_id}/status")
        )
        return HyperAgentTaskStatusResponse(**response.data)

    def stop(self, job_id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/task/hyper-agent/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    def start_and_wait(
        self,
        params: StartHyperAgentTaskParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> HyperAgentTaskResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start HyperAgent task")
        operation_name = build_operation_name("HyperAgent task ", job_id)

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
