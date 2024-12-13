from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from hyperbrowser.models.consts import ScrapeFormat

ScrapeJobStatus = Literal["pending", "running", "completed", "failed"]


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


class StartScrapeJobParams(BaseModel):
    """
    Parameters for creating a new scrape job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    use_proxy: bool = Field(default=False, serialization_alias="useProxy")
    solve_captchas: bool = Field(default=False, serialization_alias="solveCaptchas")
    options: Optional[ScrapeOptions] = None


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
    og_locale_alternate: List[str] = Field(alias="ogLocaleAlternate")
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

    job_id: str = Field(alias="jobId")
    status: ScrapeJobStatus
    error: Optional[str] = None
    data: Optional[ScrapeJobData] = None
