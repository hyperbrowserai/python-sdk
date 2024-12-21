from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from hyperbrowser.models.consts import ScrapeFormat
from hyperbrowser.models.session import CreateSessionParams

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
    wait_for: Optional[int] = Field(default=None, serialization_alias="waitFor")
    timeout: Optional[int] = Field(default=None, serialization_alias="timeout")


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


class ScrapeJobData(BaseModel):
    """
    Data from a scraped site.
    """

    metadata: Optional[dict[str, Union[str, list[str]]]] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    links: Optional[List[str]] = None


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
