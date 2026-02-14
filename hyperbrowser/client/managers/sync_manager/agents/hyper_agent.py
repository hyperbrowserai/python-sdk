from typing import Optional

from ...agent_payload_utils import build_agent_start_payload
from ...agent_status_utils import is_agent_terminal_status
from ...agent_operation_metadata import HYPER_AGENT_OPERATION_METADATA
from ...agent_route_constants import HYPER_AGENT_TASK_ROUTE_PREFIX
from ...agent_start_utils import start_agent_task
from ...agent_stop_utils import stop_agent_task
from ...agent_task_read_utils import get_agent_task, get_agent_task_status
from ...job_wait_utils import wait_for_job_result_with_defaults
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
    _OPERATION_METADATA = HYPER_AGENT_OPERATION_METADATA
    _ROUTE_PREFIX = HYPER_AGENT_TASK_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    def start(self, params: StartHyperAgentTaskParams) -> StartHyperAgentTaskResponse:
        payload = build_agent_start_payload(
            params,
            error_message="Failed to serialize HyperAgent start params",
        )
        return start_agent_task(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=StartHyperAgentTaskResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    def get(self, job_id: str) -> HyperAgentTaskResponse:
        return get_agent_task(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=HyperAgentTaskResponse,
            operation_name=self._OPERATION_METADATA.task_operation_name,
        )

    def get_status(self, job_id: str) -> HyperAgentTaskStatusResponse:
        return get_agent_task_status(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=HyperAgentTaskStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    def stop(self, job_id: str) -> BasicResponse:
        return stop_agent_task(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            operation_name=self._OPERATION_METADATA.stop_operation_name,
        )

    def start_and_wait(
        self,
        params: StartHyperAgentTaskParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> HyperAgentTaskResponse:
        job_start_resp = self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message=self._OPERATION_METADATA.start_error_message,
            operation_name_prefix=self._OPERATION_METADATA.operation_name_prefix,
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
