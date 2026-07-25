from typing import List, Optional

from typing_extensions import Required, TypedDict

from .scrape import ScrapeOptions
from .session import CreateSessionParams


class StartCrawlJobParams(TypedDict, total=False):
    """Parameters for starting a legacy crawl job."""

    url: Required[str]
    max_pages: Optional[int]
    follow_links: bool
    ignore_sitemap: bool
    exclude_patterns: List[str]
    include_patterns: List[str]
    session_options: Optional[CreateSessionParams]
    scrape_options: Optional[ScrapeOptions]


class GetCrawlJobParams(TypedDict, total=False):
    """Pagination parameters for retrieving a legacy crawl job."""

    page: Optional[int]
    batch_size: Optional[int]


__all__ = ["GetCrawlJobParams", "StartCrawlJobParams"]
