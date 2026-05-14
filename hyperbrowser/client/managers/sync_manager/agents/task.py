import time

from hyperbrowser.exceptions import HyperbrowserError
from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    AgentTaskListParams,
    AgentTaskListResponse,
    StartTaskParams,
    StartTaskResponse,
    TaskResponse,
    TaskStatusResponse,
)


class TaskManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartTaskParams) -> StartTaskResponse:
        response = self._client.transport.post(
            self._client._build_url("/task"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartTaskResponse(**response.data)

    def get(self, job_id: str) -> TaskResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/{job_id}")
        )
        return TaskResponse(**response.data)

    def get_status(self, job_id: str) -> TaskStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/{job_id}/status")
        )
        return TaskStatusResponse(**response.data)

    def stop(self, job_id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/task/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    def list(
        self, params: AgentTaskListParams = AgentTaskListParams()
    ) -> AgentTaskListResponse:
        response = self._client.transport.get(
            self._client._build_url("/task"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return AgentTaskListResponse(**response.data)

    def start_and_wait(self, params: StartTaskParams) -> TaskResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start task job")

        failures = 0
        while True:
            try:
                job_response = self.get_status(job_id)
                if job_response.status in ("completed", "failed", "stopped"):
                    return self.get(job_id)
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll task job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(2)
