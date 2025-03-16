from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from hyperbrowser.models.scrape import ScrapeOptions
from hyperbrowser.models.session import CreateSessionParams

CrawlJobStatus = Literal["pending", "running", "completed", "failed"]
CrawlPageStatus = Literal["completed", "failed"]


class StartCrawlJobParams(BaseModel):
    """
    Parameters for creating a new crawl job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    max_pages: Optional[int] = Field(default=None, ge=1, serialization_alias="maxPages")
    follow_links: bool = Field(default=True, serialization_alias="followLinks")
    ignore_sitemap: bool = Field(default=False, serialization_alias="ignoreSitemap")
    exclude_patterns: List[str] = Field(
        default=[], serialization_alias="excludePatterns"
    )
    include_patterns: List[str] = Field(
        default=[], serialization_alias="includePatterns"
    )
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
    )
    scrape_options: Optional[ScrapeOptions] = Field(
        default=None, serialization_alias="scrapeOptions"
    )


class StartCrawlJobResponse(BaseModel):
    """
    Response from creating a crawl job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class CrawlJobStatusResponse(BaseModel):
    """
    Response from getting the status of a crawl job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: CrawlJobStatus


class CrawledPage(BaseModel):
    """
    Data from a crawled page.
    """

    metadata: Optional[dict[str, Union[str, list[str]]]] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    links: Optional[List[str]] = None
    screenshot: Optional[str] = None
    url: str
    status: CrawlPageStatus
    error: Optional[str] = None


class GetCrawlJobParams(BaseModel):
    """
    Parameters for getting a crawl job.
    """

    page: Optional[int] = Field(default=None, serialization_alias="page")
    batch_size: Optional[int] = Field(
        default=None, ge=1, serialization_alias="batchSize"
    )


class CrawlJobResponse(BaseModel):
    """
    Response from getting a crawl job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: CrawlJobStatus
    error: Optional[str] = None
    data: List[CrawledPage] = Field(alias="data")
    total_crawled_pages: int = Field(alias="totalCrawledPages")
    total_page_batches: int = Field(alias="totalPageBatches")
    current_page_batch: int = Field(alias="currentPageBatch")
    batch_size: int = Field(alias="batchSize")
