from typing import Dict, List, Literal, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict

from hyperbrowser.models.consts import (
    Country,
    FetchSanitizeMode,
    FetchScreenshotFormat,
    FetchStealthMode,
    FetchWaitUntil,
    State,
)
from hyperbrowser.models.web.search import WebSearchFiletype

from ._json import JSONSchemaInput
from .session import ScreenConfig


class FetchOutputScreenshotOptions(TypedDict, total=False):
    """Screenshot-specific output settings for Web Fetch."""

    full_page: Optional[bool]
    format: Optional[FetchScreenshotFormat]
    crop_to_content: Optional[bool]
    crop_to_content_max_height: Optional[int]
    crop_to_content_min_height: Optional[int]


class FetchStorageStateOptions(TypedDict, total=False):
    """Browser storage values to seed during Web Fetch."""

    local_storage: Optional[Dict[str, str]]
    session_storage: Optional[Dict[str, str]]


class FetchBrowserLocationOptions(TypedDict, total=False):
    """Geographic browser location for Web Fetch."""

    country: Optional[Country]
    state: Optional[State]
    city: Optional[str]


class FetchOutputMarkdown(TypedDict):
    """Request Markdown output from Web Fetch."""

    type: Literal["markdown"]


class FetchOutputHtml(TypedDict):
    """Request HTML output from Web Fetch."""

    type: Literal["html"]


class FetchOutputLinks(TypedDict):
    """Request extracted link output from Web Fetch."""

    type: Literal["links"]


class FetchOutputScreenshot(FetchOutputScreenshotOptions, total=False):
    """Request screenshot output from Web Fetch."""

    type: Required[Literal["screenshot"]]


class FetchOutputJsonOptions(TypedDict, total=False):
    """Prompt and schema options for structured JSON output."""

    prompt: Optional[str]
    schema: Optional[JSONSchemaInput]


class FetchOutputJson(FetchOutputJsonOptions, total=False):
    """Request schema-guided JSON output from Web Fetch."""

    type: Required[Literal["json"]]


class FetchOutputBranding(TypedDict):
    """Request detected branding output from Web Fetch."""

    type: Literal["branding"]


FetchOutputFormat: TypeAlias = Union[
    FetchOutputMarkdown,
    FetchOutputHtml,
    FetchOutputLinks,
    FetchOutputScreenshot,
    FetchOutputJson,
    FetchOutputBranding,
    Literal["markdown", "html", "links", "screenshot", "branding"],
]


class FetchOutputOptions(TypedDict, total=False):
    """Output formats and content filtering for Web Fetch."""

    formats: Optional[List[FetchOutputFormat]]
    sanitize: Optional[FetchSanitizeMode]
    include_selectors: Optional[List[str]]
    exclude_selectors: Optional[List[str]]
    storage_state: Optional[FetchStorageStateOptions]


class FetchBrowserOptions(TypedDict, total=False):
    """Browser profile, viewport, CAPTCHA, and location options."""

    screen: Optional[ScreenConfig]
    profile_id: Optional[str]
    solve_captchas: Optional[bool]
    location: Optional[FetchBrowserLocationOptions]


class FetchNavigationOptions(TypedDict, total=False):
    """Navigation timing and wait behavior for Web Fetch."""

    wait_until: Optional[FetchWaitUntil]
    timeout_ms: Optional[int]
    wait_for: Optional[int]


class FetchCacheOptions(TypedDict, total=False):
    """Cache freshness settings for Web Fetch."""

    max_age_seconds: Optional[int]


class FetchParams(TypedDict, total=False):
    """Parameters for fetching and processing one web page."""

    url: Required[str]
    stealth: Optional[FetchStealthMode]
    outputs: Optional[FetchOutputOptions]
    browser: Optional[FetchBrowserOptions]
    navigation: Optional[FetchNavigationOptions]
    cache: Optional[FetchCacheOptions]


class StartBatchFetchJobParams(TypedDict, total=False):
    """Parameters for starting a batch Web Fetch job."""

    urls: Required[List[str]]
    stealth: Optional[FetchStealthMode]
    outputs: Optional[FetchOutputOptions]
    browser: Optional[FetchBrowserOptions]
    navigation: Optional[FetchNavigationOptions]
    cache: Optional[FetchCacheOptions]


class GetBatchFetchJobParams(TypedDict, total=False):
    """Pagination parameters for retrieving a batch fetch job."""

    page: Optional[int]
    batch_size: Optional[int]


class WebCrawlOptions(TypedDict, total=False):
    """Link traversal and URL filtering options for Web Crawl."""

    max_pages: Optional[int]
    ignore_sitemap: Optional[bool]
    follow_links: Optional[bool]
    exclude_patterns: Optional[List[str]]
    include_patterns: Optional[List[str]]


class StartWebCrawlJobParams(TypedDict, total=False):
    """Parameters for starting a Web Crawl job."""

    url: Required[str]
    stealth: Optional[FetchStealthMode]
    outputs: Optional[FetchOutputOptions]
    browser: Optional[FetchBrowserOptions]
    navigation: Optional[FetchNavigationOptions]
    cache: Optional[FetchCacheOptions]
    crawl_options: Optional[WebCrawlOptions]


class GetWebCrawlJobParams(TypedDict, total=False):
    """Pagination parameters for retrieving a Web Crawl job."""

    page: Optional[int]
    batch_size: Optional[int]


class WebSearchFilters(TypedDict, total=False):
    """Query filters for Web Search."""

    exact_phrase: Optional[bool]
    semantic_phrase: Optional[bool]
    exclude_terms: Optional[List[str]]
    boost_terms: Optional[List[str]]
    filetype: Optional[WebSearchFiletype]
    site: Optional[str]
    exclude_site: Optional[str]
    intitle: Optional[str]
    inurl: Optional[str]


class WebSearchLocation(TypedDict, total=False):
    """Geographic location used to localize Web Search."""

    country: Optional[Country]
    state: Optional[State]
    city: Optional[str]


class WebSearchParams(TypedDict, total=False):
    """Parameters for a Web Search request."""

    query: Required[str]
    page: Optional[int]
    max_age_seconds: Optional[int]
    location: Optional[WebSearchLocation]
    filters: Optional[WebSearchFilters]


__all__ = [
    "FetchBrowserLocationOptions",
    "FetchBrowserOptions",
    "FetchCacheOptions",
    "FetchNavigationOptions",
    "FetchOutputBranding",
    "FetchOutputFormat",
    "FetchOutputHtml",
    "FetchOutputJson",
    "FetchOutputJsonOptions",
    "FetchOutputLinks",
    "FetchOutputMarkdown",
    "FetchOutputOptions",
    "FetchOutputScreenshot",
    "FetchOutputScreenshotOptions",
    "FetchParams",
    "FetchStorageStateOptions",
    "GetBatchFetchJobParams",
    "GetWebCrawlJobParams",
    "StartBatchFetchJobParams",
    "StartWebCrawlJobParams",
    "WebCrawlOptions",
    "WebSearchFilters",
    "WebSearchLocation",
    "WebSearchParams",
]
