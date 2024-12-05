from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

ScrapeJobStatus = Literal["pending", "running", "completed", "failed"]


class StartScrapeJobParams(BaseModel):
    """
    Parameters for creating a new scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str


class StartScrapeJobResponse(BaseModel):
    """
    Response from creating a scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class ScrapeJobMetadata(BaseModel):
    """
    Metadata for the scraped site.
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
    og_locale_alternate: list[str] = Field(alias="ogLocaleAlternate")
    og_site_name: str = Field(alias="ogSiteName")
    source_url: str = Field(alias="sourceURL")


class ScrapeJobData(BaseModel):
    """
    Data from a scraped site.
    """

    metadata: ScrapeJobMetadata
    markdown: str


class ScrapeJobResponse(BaseModel):
    """
    Response from getting a scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: ScrapeJobStatus
    error: Optional[str] = None
    data: Optional[ScrapeJobData] = None
