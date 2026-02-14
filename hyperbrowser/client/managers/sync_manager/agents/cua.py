from typing import Optional

from ...agent_payload_utils import build_agent_start_payload
from ...agent_status_utils import is_agent_terminal_status
from ...agent_stop_utils import stop_agent_task
from ...agent_task_read_utils import get_agent_task, get_agent_task_status
from ...job_wait_utils import wait_for_job_result_with_defaults
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context

from .....models import (
    BasicResponse,
    CuaTaskResponse,
    CuaTaskStatusResponse,
    StartCuaTaskParams,
    StartCuaTaskResponse,
)
from ...polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)


class CuaManager:
    _ROUTE_PREFIX = "/task/cua"

    def __init__(self, client):
        self._client = client

    def start(self, params: StartCuaTaskParams) -> StartCuaTaskResponse:
        payload = build_agent_start_payload(
            params,
            error_message="Failed to serialize CUA start params",
        )
        response = self._client.transport.post(
            self._client._build_url(self._ROUTE_PREFIX),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartCuaTaskResponse,
            operation_name="cua start",
        )

    def get(self, job_id: str) -> CuaTaskResponse:
        return get_agent_task(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=CuaTaskResponse,
            operation_name="cua task",
        )

    def get_status(self, job_id: str) -> CuaTaskStatusResponse:
        return get_agent_task_status(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=CuaTaskStatusResponse,
            operation_name="cua task status",
        )

    def stop(self, job_id: str) -> BasicResponse:
        return stop_agent_task(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            operation_name="cua task stop",
        )

    def start_and_wait(
        self,
        params: StartCuaTaskParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> CuaTaskResponse:
        job_start_resp = self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start CUA task job",
            operation_name_prefix="CUA task job ",
        )

        return wait_for_job_result_with_defaults(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_agent_terminal_status,
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )
