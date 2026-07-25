import time
from typing import Union

from hyperbrowser.client._request import dump_request
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.types import StartCuaTaskParams as StartCuaTaskParamsDict

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    CuaTaskResponse,
    CuaTaskStatusResponse,
    StartCuaTaskParams,
    StartCuaTaskResponse,
)


class CuaManager:
    def __init__(self, client):
        self._client = client

    def start(
        self,
        params: Union[StartCuaTaskParamsDict, StartCuaTaskParams],
    ) -> StartCuaTaskResponse:
        response = self._client.transport.post(
            self._client._build_url("/task/cua"),
            data=dump_request(params, StartCuaTaskParams),
        )
        return StartCuaTaskResponse(**response.data)

    def get(self, job_id: str) -> CuaTaskResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/cua/{job_id}")
        )
        return CuaTaskResponse(**response.data)

    def get_status(self, job_id: str) -> CuaTaskStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/cua/{job_id}/status")
        )
        return CuaTaskStatusResponse(**response.data)

    def stop(self, job_id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/task/cua/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    def start_and_wait(
        self,
        params: Union[StartCuaTaskParamsDict, StartCuaTaskParams],
    ) -> CuaTaskResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start CUA task job")

        failures = 0
        while True:
            try:
                job_response = self.get_status(job_id)
                if (
                    job_response.status == "completed"
                    or job_response.status == "failed"
                    or job_response.status == "stopped"
                ):
                    return self.get(job_id)
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll CUA task job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(2)
