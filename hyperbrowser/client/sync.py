import time
from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.crawl import (
    CrawlJobResponse,
    GetCrawlJobParams,
    StartCrawlJobParams,
    StartCrawlJobResponse,
)
from hyperbrowser.models.scrape import (
    ScrapeJobResponse,
    StartScrapeJobParams,
    StartScrapeJobResponse,
)
from ..transport.sync import SyncTransport
from .base import HyperbrowserBase
from ..models.session import (
    BasicResponse,
    CreateSessionParams,
    SessionDetail,
    SessionListParams,
    SessionListResponse,
)
from ..config import ClientConfig


class Hyperbrowser(HyperbrowserBase):
    """Synchronous Hyperbrowser client"""

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(SyncTransport, config, api_key, base_url)

    def create_session(self, params: CreateSessionParams) -> SessionDetail:
        response = self.transport.post(
            self._build_url("/session"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SessionDetail(**response.data)

    def get_session(self, id: str) -> SessionDetail:
        response = self.transport.get(self._build_url(f"/session/{id}"))
        return SessionDetail(**response.data)

    def stop_session(self, id: str) -> BasicResponse:
        response = self.transport.put(self._build_url(f"/session/{id}/stop"))
        return BasicResponse(**response.data)

    def get_session_list(self, params: SessionListParams) -> SessionListResponse:
        response = self.transport.get(
            self._build_url("/sessions"), params=params.__dict__
        )
        return SessionListResponse(**response.data)

    def start_scrape_job(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        response = self.transport.post(
            self._build_url("/scrape"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartScrapeJobResponse(**response.data)

    def get_scrape_job(self, job_id: str) -> ScrapeJobResponse:
        response = self.transport.get(self._build_url(f"/scrape/{job_id}"))
        return ScrapeJobResponse(**response.data)

    def start_crawl_job(self, params: StartCrawlJobParams) -> StartCrawlJobResponse:
        response = self.transport.post(
            self._build_url("/crawl"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartCrawlJobResponse(**response.data)

    def get_crawl_job(
        self, job_id: str, params: GetCrawlJobParams = GetCrawlJobParams()
    ) -> CrawlJobResponse:
        response = self.transport.get(
            self._build_url(f"/crawl/{job_id}"), params=params.__dict__
        )
        return CrawlJobResponse(**response.data)

    def start_scrape_job_and_wait_until_complete(
        self, params: StartScrapeJobParams
    ) -> ScrapeJobResponse:
        job_id = self.start_scrape_job(params)
        if not job_id:
            raise HyperbrowserError("Failed to start scrape job")
        while True:
            job = self.get_scrape_job(job_id)
            if job.status == "completed" or job.status == "failed":
                return job
            time.sleep(2)

    def start_crawl_job_and_wait_until_complete(
        self, params: StartCrawlJobParams
    ) -> CrawlJobResponse:
        job_id = self.start_crawl_job(params)
        if not job_id:
            raise HyperbrowserError("Failed to start crawl job")
        while True:
            job = self.get_crawl_job(job_id)
            if job.status == "completed" or job.status == "failed":
                return job
            time.sleep(2)

    def close(self) -> None:
        self.transport.close()
