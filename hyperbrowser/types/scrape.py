from typing import Dict, List, Optional

from typing_extensions import Required, TypedDict

from hyperbrowser.models.consts import (
    ScrapeFormat,
    ScrapeScreenshotFormat,
    ScrapeWaitUntil,
)

from .session import CreateSessionParams


class ScreenshotOptions(TypedDict, total=False):
    """Screenshot options for a scrape request."""

    full_page: Optional[bool]
    format: Optional[ScrapeScreenshotFormat]
    crop_to_content: Optional[bool]
    crop_to_content_max_height: Optional[int]
    crop_to_content_min_height: Optional[int]
    wait_for: Optional[int]


class StorageStateOptions(TypedDict, total=False):
    """Browser storage values to seed before scraping."""

    local_storage: Optional[Dict[str, str]]
    session_storage: Optional[Dict[str, str]]


class ScrapeOptions(TypedDict, total=False):
    """Content, waiting, screenshot, and storage options for scraping."""

    formats: Optional[List[ScrapeFormat]]
    include_tags: Optional[List[str]]
    exclude_tags: Optional[List[str]]
    only_main_content: Optional[bool]
    wait_for: Optional[int]
    timeout: Optional[int]
    wait_until: Optional[ScrapeWaitUntil]
    screenshot_options: Optional[ScreenshotOptions]
    storage_state: Optional[StorageStateOptions]


class StartScrapeJobParams(TypedDict, total=False):
    """Parameters for starting a single-page scrape job."""

    url: Required[str]
    session_options: Optional[CreateSessionParams]
    scrape_options: Optional[ScrapeOptions]


class StartBatchScrapeJobParams(TypedDict, total=False):
    """Parameters for starting a batch scrape job."""

    urls: Required[List[str]]
    session_options: Optional[CreateSessionParams]
    scrape_options: Optional[ScrapeOptions]


class GetBatchScrapeJobParams(TypedDict, total=False):
    """Pagination parameters for retrieving a batch scrape job."""

    page: Optional[int]
    batch_size: Optional[int]


__all__ = [
    "GetBatchScrapeJobParams",
    "ScrapeOptions",
    "ScreenshotOptions",
    "StartBatchScrapeJobParams",
    "StartScrapeJobParams",
    "StorageStateOptions",
]
