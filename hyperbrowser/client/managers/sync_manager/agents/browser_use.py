import time

from hyperbrowser.exceptions import HyperbrowserError

from .....models import (
    POLLING_ATTEMPTS,
    BasicResponse,
    BrowserUseTaskResponse,
    BrowserUseTaskStatusResponse,
    StartBrowserUseTaskParams,
    StartBrowserUseTaskResponse,
)


class BrowserUseManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartBrowserUseTaskParams) -> StartBrowserUseTaskResponse:
        response = self._client.transport.post(
            self._client._build_url("/task/browser-use"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartBrowserUseTaskResponse(**response.data)

    def get(self, job_id: str) -> BrowserUseTaskResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/browser-use/{job_id}")
        )
        return BrowserUseTaskResponse(**response.data)

    def get_status(self, job_id: str) -> BrowserUseTaskStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/task/browser-use/{job_id}/status")
        )
        return BrowserUseTaskStatusResponse(**response.data)

    def stop(self, job_id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/task/browser-use/{job_id}/stop")
        )
        return BasicResponse(**response.data)

    def start_and_wait(
        self, params: StartBrowserUseTaskParams
    ) -> BrowserUseTaskResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start browser-use task job")

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
                        f"Failed to poll browser-use task job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(2)
