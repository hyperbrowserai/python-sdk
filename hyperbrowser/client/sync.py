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

    def scrape_and_wait_until_complete(
        self, params: StartScrapeJobParams
    ) -> ScrapeJobResponse:
        job_start_resp = self.start_scrape_job(params)
        if not job_start_resp.job_id:
            raise HyperbrowserError("Failed to start scrape job")
        while True:
            job_response = self.get_scrape_job(job_start_resp.job_id)
            if job_response.status == "completed" or job_response.status == "failed":
                return job_response
            time.sleep(2)

    def crawl_and_wait_until_complete(
        self, params: StartCrawlJobParams, return_all_pages: bool = True
    ) -> CrawlJobResponse:
        job_start_resp = self.start_crawl_job(params)
        if not job_start_resp.job_id:
            raise HyperbrowserError("Failed to start crawl job")

        job_response: CrawlJobResponse
        while True:
            job_response = self.get_crawl_job(job_start_resp.job_id)
            if job_response.status == "completed" or job_response.status == "failed":
                break
            time.sleep(2)

        if not return_all_pages:
            return job_response

        while job_response.current_page_batch < job_response.total_page_batches:
            tmp_job_response = self.get_crawl_job(
                job_start_resp.job_id,
                GetCrawlJobParams(page=job_response.current_page_batch + 1),
            )
            if tmp_job_response.data:
                job_response.data.extend(tmp_job_response.data)
            job_response.current_page_batch = tmp_job_response.current_page_batch
            job_response.total_crawled_pages = tmp_job_response.total_crawled_pages
            job_response.total_page_batches = tmp_job_response.total_page_batches
            job_response.batch_size = tmp_job_response.batch_size
            time.sleep(0.5)
        return job_response

    def close(self) -> None:
        self.transport.close()
