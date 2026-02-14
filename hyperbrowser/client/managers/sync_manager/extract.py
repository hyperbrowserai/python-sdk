from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.consts import POLLING_ATTEMPTS
from hyperbrowser.models.extract import (
    ExtractJobResponse,
    ExtractJobStatusResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)
from ...polling import build_operation_name, ensure_started_job_id, wait_for_job_result
from ..serialization_utils import serialize_model_dump_to_dict
from ...schema_utils import resolve_schema_input
from ..response_utils import parse_response_model


class ExtractManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        if not params.schema_ and not params.prompt:
            raise HyperbrowserError("Either schema or prompt must be provided")

        payload = serialize_model_dump_to_dict(
            params,
            error_message="Failed to serialize extract start params",
        )
        if params.schema_:
            payload["schema"] = resolve_schema_input(params.schema_)

        response = self._client.transport.post(
            self._client._build_url("/extract"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartExtractJobResponse,
            operation_name="extract start",
        )

    def get_status(self, job_id: str) -> ExtractJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobStatusResponse,
            operation_name="extract status",
        )

    def get(self, job_id: str) -> ExtractJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=ExtractJobResponse,
            operation_name="extract job",
        )

    def start_and_wait(
        self,
        params: StartExtractJobParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> ExtractJobResponse:
        job_start_resp = self.start(params)
        job_id = ensure_started_job_id(
            job_start_resp.job_id,
            error_message="Failed to start extract job",
        )
        operation_name = build_operation_name("extract job ", job_id)

        return wait_for_job_result(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
            fetch_max_attempts=POLLING_ATTEMPTS,
            fetch_retry_delay_seconds=0.5,
        )
