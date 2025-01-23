import time
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extract import (
    ExtractJobResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)


class ExtractManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        if not params.schema_ and not params.prompt:
            raise HyperbrowserError("Either schema or prompt must be provided")
        if params.schema_:
            if hasattr(params.schema_, "model_json_schema"):
                params.schema_ = params.schema_.model_json_schema()

        response = self._client.transport.post(
            self._client._build_url("/extract"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartExtractJobResponse(**response.data)

    def get(self, job_id: str) -> ExtractJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}")
        )
        return ExtractJobResponse(**response.data)

    def start_and_wait(self, params: StartExtractJobParams) -> ExtractJobResponse:
        job_start_resp = self.start(params)
        if not job_start_resp.job_id:
            raise HyperbrowserError("Failed to start extract job")
        while True:
            job_response = self.get(job_start_resp.job_id)
            if job_response.status == "completed" or job_response.status == "failed":
                return job_response
            time.sleep(2)
