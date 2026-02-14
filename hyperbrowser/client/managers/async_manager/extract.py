from typing import Optional

from hyperbrowser.models.extract import (
    ExtractJobResponse,
    ExtractJobStatusResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)
from ..extract_payload_utils import build_extract_start_payload
from ..job_operation_metadata import EXTRACT_OPERATION_METADATA
from ..job_route_constants import EXTRACT_JOB_ROUTE_PREFIX
from ..job_status_utils import is_default_terminal_job_status
from ..job_wait_utils import wait_for_job_result_with_defaults_async
from ..polling_defaults import (
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from ..start_job_utils import build_started_job_context
from ..response_utils import parse_response_model


class ExtractManager:
    _OPERATION_METADATA = EXTRACT_OPERATION_METADATA
    _ROUTE_PREFIX = EXTRACT_JOB_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    async def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        payload = build_extract_start_payload(params)

        response = await self._client.transport.post(
            self._client._build_url(self._ROUTE_PREFIX),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartExtractJobResponse,
            operation_name=self._OPERATION_METADATA.start_operation_name,
        )

    async def get_status(self, job_id: str) -> ExtractJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"{self._ROUTE_PREFIX}/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobStatusResponse,
            operation_name=self._OPERATION_METADATA.status_operation_name,
        )

    async def get(self, job_id: str) -> ExtractJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"{self._ROUTE_PREFIX}/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobResponse,
            operation_name=self._OPERATION_METADATA.job_operation_name,
        )

    async def start_and_wait(
        self,
        params: StartExtractJobParams,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: Optional[float] = DEFAULT_MAX_WAIT_SECONDS,
        max_status_failures: int = DEFAULT_POLLING_RETRY_ATTEMPTS,
    ) -> ExtractJobResponse:
        job_start_resp = await self.start(params)
        job_id, operation_name = build_started_job_context(
            started_job_id=job_start_resp.job_id,
            start_error_message=self._OPERATION_METADATA.start_error_message,
            operation_name_prefix=self._OPERATION_METADATA.operation_name_prefix,
        )

        return await wait_for_job_result_with_defaults_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=is_default_terminal_job_status,
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )
