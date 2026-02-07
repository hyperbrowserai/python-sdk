from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from .common import (
    PageData,
    FetchOutputOptions,
    FetchNavigationOptions,
    FetchBrowserOptions,
    FetchCacheOptions,
)
from hyperbrowser.models.consts import WebCrawlJobStatus, FetchStealthMode


class WebCrawlOptions(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    max_pages: Optional[int] = Field(default=None, serialization_alias="maxPages")
    ignore_sitemap: Optional[bool] = Field(
        default=None, serialization_alias="ignoreSitemap"
    )
    follow_links: Optional[bool] = Field(
        default=None, serialization_alias="followLinks"
    )
    exclude_patterns: Optional[List[str]] = Field(
        default=None, serialization_alias="excludePatterns"
    )
    include_patterns: Optional[List[str]] = Field(
        default=None, serialization_alias="includePatterns"
    )


class StartWebCrawlJobParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    stealth: Optional[FetchStealthMode] = Field(
        default=None, serialization_alias="stealth"
    )
    outputs: Optional[FetchOutputOptions] = Field(
        default=None, serialization_alias="outputs"
    )
    browser: Optional[FetchBrowserOptions] = Field(
        default=None, serialization_alias="browser"
    )
    navigation: Optional[FetchNavigationOptions] = Field(
        default=None, serialization_alias="navigation"
    )
    cache: Optional[FetchCacheOptions] = Field(
        default=None, serialization_alias="cache"
    )
    crawl_options: Optional[WebCrawlOptions] = Field(
        default=None, serialization_alias="crawlOptions"
    )


class GetWebCrawlJobParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    page: Optional[int] = Field(default=None, serialization_alias="page")
    batch_size: Optional[int] = Field(
        default=None, ge=1, serialization_alias="batchSize"
    )


class StartWebCrawlJobResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class WebCrawlJobStatusResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: WebCrawlJobStatus


class WebCrawlJobResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: WebCrawlJobStatus
    error: Optional[str] = None
    data: Optional[List[PageData]] = Field(default=None, alias="data")
    total_pages: int = Field(alias="totalPages")
    total_page_batches: int = Field(alias="totalPageBatches")
    current_page_batch: int = Field(alias="currentPageBatch")
    batch_size: int = Field(alias="batchSize")
