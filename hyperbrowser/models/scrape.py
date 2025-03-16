from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from hyperbrowser.models.consts import (
    ScrapeFormat,
    ScrapePageStatus,
    ScrapeScreenshotFormat,
    ScrapeWaitUntil,
)
from hyperbrowser.models.session import CreateSessionParams

ScrapeJobStatus = Literal["pending", "running", "completed", "failed"]


class ScreenshotOptions(BaseModel):
    """
    Options for screenshot.
    """

    full_page: Optional[bool] = Field(default=None, serialization_alias="fullPage")
    format: Optional[ScrapeScreenshotFormat] = Field(
        default=None, serialization_alias="format"
    )


class ScrapeOptions(BaseModel):
    """
    Options for scraping a page.
    """

    formats: Optional[List[ScrapeFormat]] = None
    include_tags: Optional[List[str]] = Field(
        default=None, serialization_alias="includeTags"
    )
    exclude_tags: Optional[List[str]] = Field(
        default=None, serialization_alias="excludeTags"
    )
    only_main_content: Optional[bool] = Field(
        default=None, serialization_alias="onlyMainContent"
    )
    wait_for: Optional[int] = Field(default=None, serialization_alias="waitFor")
    timeout: Optional[int] = Field(default=None, serialization_alias="timeout")
    wait_until: Optional[ScrapeWaitUntil] = Field(
        default=None, serialization_alias="waitUntil"
    )
    screenshot_options: Optional[ScreenshotOptions] = Field(
        default=None, serialization_alias="screenshotOptions"
    )


class StartScrapeJobParams(BaseModel):
    """
    Parameters for creating a new scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
    )
    scrape_options: Optional[ScrapeOptions] = Field(
        default=None, serialization_alias="scrapeOptions"
    )


class StartScrapeJobResponse(BaseModel):
    """
    Response from creating a scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class ScrapeJobStatusResponse(BaseModel):
    """
    Response from getting the status of a scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: ScrapeJobStatus


class ScrapeJobData(BaseModel):
    """
    Data from a scraped site.
    """

    metadata: Optional[dict[str, Union[str, list[str]]]] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    links: Optional[List[str]] = None
    screenshot: Optional[str] = None


class ScrapeJobResponse(BaseModel):
    """
    Response from getting a scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: ScrapeJobStatus
    error: Optional[str] = None
    data: Optional[ScrapeJobData] = None


class StartBatchScrapeJobParams(BaseModel):
    """
    Parameters for creating a new batch scrape job.
    """

    urls: List[str]
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
    )
    scrape_options: Optional[ScrapeOptions] = Field(
        default=None, serialization_alias="scrapeOptions"
    )


class BatchScrapeJobStatusResponse(BaseModel):
    """
    Response from getting the status of a batch scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: ScrapeJobStatus


class ScrapedPage(BaseModel):
    """
    A scraped page.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    status: ScrapePageStatus
    error: Optional[str] = None
    metadata: Optional[dict[str, Union[str, list[str]]]] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    links: Optional[List[str]] = None
    screenshot: Optional[str] = None


class GetBatchScrapeJobParams(BaseModel):
    """
    Parameters for getting a batch scrape job.
    """

    page: Optional[int] = Field(default=None, serialization_alias="page")
    batch_size: Optional[int] = Field(
        default=None, ge=1, serialization_alias="batchSize"
    )


class StartBatchScrapeJobResponse(BaseModel):
    """
    Response from starting a batch scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class BatchScrapeJobResponse(BaseModel):
    """
    Response from getting a batch scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: ScrapeJobStatus
    error: Optional[str] = None
    data: Optional[List[ScrapedPage]] = Field(alias="data")
    total_scraped_pages: int = Field(alias="totalScrapedPages")
    total_page_batches: int = Field(alias="totalPageBatches")
    current_page_batch: int = Field(alias="currentPageBatch")
    batch_size: int = Field(alias="batchSize")
