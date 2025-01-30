import asyncio
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.consts import POLLING_ATTEMPTS
from hyperbrowser.models.extract import (
    ExtractJobResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)


class ExtractManager:
    def __init__(self, client):
        self._client = client

    async def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        if not params.schema_ and not params.prompt:
            raise HyperbrowserError("Either schema or prompt must be provided")
        if params.schema_:
            if hasattr(params.schema_, "model_json_schema"):
                params.schema_ = params.schema_.model_json_schema()

        response = await self._client.transport.post(
            self._client._build_url("/extract"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartExtractJobResponse(**response.data)

    async def get(self, job_id: str) -> ExtractJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}")
        )
        return ExtractJobResponse(**response.data)

    async def start_and_wait(self, params: StartExtractJobParams) -> ExtractJobResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start extract job")

        failures = 0
        while True:
            try:
                job_response = await self.get(job_id)
                if (
                    job_response.status == "completed"
                    or job_response.status == "failed"
                ):
                    return job_response
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll extract job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            await asyncio.sleep(2)
