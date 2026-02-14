from typing import Optional

from ...agent_status_utils import is_agent_terminal_status
from ...browser_use_payload_utils import build_browser_use_start_payload
from ...agent_route_constants import BROWSER_USE_TASK_ROUTE_PREFIX
from ...agent_stop_utils import stop_agent_task_async
from ...agent_task_read_utils import get_agent_task_async, get_agent_task_status_async
from ...job_wait_utils import wait_for_job_result_with_defaults_async
from ...response_utils import parse_response_model
from ...start_job_utils import build_started_job_context

from .....models import (
    BasicResponse,
    BrowserUseTaskResponse,
    BrowserUseTaskStatusResponse,
    StartBrowserUseTaskParams,
    StartBrowserUseTaskResponse,
)
from ...polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)


class BrowserUseManager:
    _ROUTE_PREFIX = BROWSER_USE_TASK_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartBrowserUseTaskParams
    ) -> StartBrowserUseTaskResponse:
        payload = build_browser_use_start_payload(params)
        response = await self._client.transport.post(
            self._client._build_url(self._ROUTE_PREFIX),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartBrowserUseTaskResponse,
            operation_name="browser-use start",
        )

    async def get(self, job_id: str) -> BrowserUseTaskResponse:
        return await get_agent_task_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=BrowserUseTaskResponse,
            operation_name="browser-use task",
        )

    async def get_status(self, job_id: str) -> BrowserUseTaskStatusResponse:
        return await get_agent_task_status_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            model=BrowserUseTaskStatusResponse,
            operation_name="browser-use task status",
        )

    async def stop(self, job_id: str) -> BasicResponse:
        return await stop_agent_task_async(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            job_id=job_id,
            operation_name="browser-use task stop",
        )

    async def start_and_wait(
        self,
        params: StartBrowserUseTaskParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> BrowserUseTaskResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message="Failed to start browser-use task job",
            operation_name_prefix="browser-use task job ",
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
