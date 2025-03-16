import asyncio
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.consts import POLLING_ATTEMPTS
from hyperbrowser.models.extract import (
    ExtractJobResponse,
    ExtractJobStatusResponse,
    StartExtractJobParams,
    StartExtractJobResponse,
)
import jsonref


class ExtractManager:
    def __init__(self, client):
        self._client = client

    async def start(self, params: StartExtractJobParams) -> StartExtractJobResponse:
        if not params.schema_ and not params.prompt:
            raise HyperbrowserError("Either schema or prompt must be provided")
        if params.schema_:
            if hasattr(params.schema_, "model_json_schema"):
                params.schema_ = jsonref.replace_refs(
                    params.schema_.model_json_schema(), proxies=False, lazy_load=False
                )

        response = await self._client.transport.post(
            self._client._build_url("/extract"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartExtractJobResponse(**response.data)

    async def get_status(self, job_id: str) -> ExtractJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/extract/{job_id}/status")
        )
        return ExtractJobStatusResponse(**response.data)

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
                job_status_resp = await self.get_status(job_id)
                job_status = job_status_resp.status
                if job_status == "completed" or job_status == "failed":
                    return await self.get(job_id)
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll extract job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            await asyncio.sleep(2)
