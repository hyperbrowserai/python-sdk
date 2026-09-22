import asyncio
from typing import Union

from hyperbrowser.client._request import dump_request
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.types import (
    StartJevComputerUseTaskParams as StartJevComputerUseTaskParamsDict,
)

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    JevComputerUseTaskResponse,
    JevComputerUseTaskStatusResponse,
    StartJevComputerUseTaskParams,
    StartJevComputerUseTaskResponse,
)


class JevComputerUseManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self,
        params: Union[
            StartJevComputerUseTaskParamsDict,
            StartJevComputerUseTaskParams,
        ],
    ) -> StartJevComputerUseTaskResponse:
        response = await self._client.transport.post(
            self._client._build_url("/task/jev"),
            data=dump_request(params, StartJevComputerUseTaskParams),
        )
        return StartJevComputerUseTaskResponse(**response.data)

    async def get(self, job_id: str) -> JevComputerUseTaskResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/jev/{job_id}")
        )
        return JevComputerUseTaskResponse(**response.data)

    async def get_status(self, job_id: str) -> JevComputerUseTaskStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/task/jev/{job_id}/status")
        )
        return JevComputerUseTaskStatusResponse(**response.data)

    async def stop(self, job_id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/task/jev/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    async def start_and_wait(
        self,
        params: Union[
            StartJevComputerUseTaskParamsDict,
            StartJevComputerUseTaskParams,
        ],
    ) -> JevComputerUseTaskResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start Jev Computer Use task job")

        failures = 0
        while True:
            try:
                job_response = await self.get_status(job_id)
                if (
                    job_response.status == "completed"
                    or job_response.status == "failed"
                    or job_response.status == "stopped"
                ):
                    return await self.get(job_id)
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll Jev Computer Use task job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            await asyncio.sleep(2)
