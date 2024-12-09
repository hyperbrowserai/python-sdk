from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

CrawlJobStatus = Literal["pending", "running", "completed", "failed"]


class StartCrawlJobParams(BaseModel):
    """
    Parameters for creating a new crawl job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    max_pages: int = Field(default=10, ge=1, le=50, serialization_alias="maxPages")
    follow_links: bool = Field(default=True, serialization_alias="followLinks")
    exclude_patterns: List[str] = Field(
        default=[], serialization_alias="excludePatterns"
    )
    include_patterns: List[str] = Field(
        default=[], serialization_alias="includePatterns"
    )
    use_proxy: bool = Field(default=False, serialization_alias="useProxy")
    solve_captchas: bool = Field(default=False, serialization_alias="solveCaptchas")


class StartCrawlJobResponse(BaseModel):
    """
    Response from creating a crawl job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class CrawledPageMetadata(BaseModel):
    """
    Metadata for the crawled page.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    title: str
    description: str
    robots: str
    og_title: str = Field(alias="ogTitle")
    og_description: str = Field(alias="ogDescription")
    og_url: str = Field(alias="ogUrl")
    og_image: str = Field(alias="ogImage")
    og_locale_alternate: List[str] = Field(alias="ogLocaleAlternate")
    og_site_name: str = Field(alias="ogSiteName")
    source_url: str = Field(alias="sourceURL")


class CrawledPage(BaseModel):
    """
    Data from a crawled page.
    """

    metadata: CrawledPageMetadata
    markdown: str
    url: str


class GetCrawlJobParams(BaseModel):
    """
    Parameters for getting a crawl job.
    """

    page: Optional[int] = Field(default=None, serialization_alias="page")
    batch_size: Optional[int] = Field(
        default=10, ge=1, le=50, serialization_alias="batchSize"
    )


class CrawlJobResponse(BaseModel):
    """
    Response from getting a crawl job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: CrawlJobStatus
    error: Optional[str] = None
    data: List[CrawledPage] = Field(alias="data")
    total_crawled_pages: int = Field(alias="totalCrawledPages")
    total_page_batches: int = Field(alias="totalPageBatches")
    current_page_batch: int = Field(alias="currentPageBatch")
    batch_size: int = Field(alias="batchSize")
