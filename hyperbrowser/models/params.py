# Public TypedDict param types mirroring the Pydantic request models, plus the
# ``coerce_to_model`` helper managers use to accept either form. Keep these in
# sync with the corresponding Pydantic models (field names and requiredness).
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Type, TypeVar, Union
from typing_extensions import TypedDict, Required
from pydantic import BaseModel
from hyperbrowser.models.agents.browser_use import BrowserUseLlm, BrowserUseVersion
from hyperbrowser.models.agents.claude_computer_use import ClaudeComputerUseLlm
from hyperbrowser.models.agents.cua import CuaLlm
from hyperbrowser.models.agents.gemini_computer_use import GeminiComputerUseLlm
from hyperbrowser.models.agents.grok_computer_use import (
    GrokComputerUseLlm,
    GrokReasoningEffort,
)
from hyperbrowser.models.agents.hyper_agent import HyperAgentLlm, HyperAgentVersion
from hyperbrowser.models.scrape import (
    ScrapeFormat,
    ScrapeScreenshotFormat,
    ScrapeWaitUntil,
)
from hyperbrowser.models.session import (
    BrowserMemorySize,
    CaptchaEvaluationType,
    CaptchaSolverType,
    Country,
    ISO639_1,
    OperatingSystem,
    Platform,
    SessionEventLogType,
    SessionRegion,
    SessionStatus,
    State,
)
from hyperbrowser.models.web.batch_fetch import FetchStealthMode
from hyperbrowser.models.web.common import (
    FetchOutputFormat,
    FetchSanitizeMode,
    FetchScreenshotFormat,
    FetchWaitUntil,
)
from hyperbrowser.models.web.search import WebSearchFiletype


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def coerce_to_model(
    model_cls: Type[_ModelT],
    params: Optional[Union[_ModelT, Dict[str, Any]]],
) -> _ModelT:
    """Coerce a TypedDict/plain dict or model instance into ``model_cls``.

    Passing a dict validates it through the Pydantic model so that wire
    serialization (aliases, nested models, user-supplied JSON schema fields)
    is byte-for-byte identical to passing the model directly. Existing model
    instances are returned unchanged, and ``None`` yields an empty model.
    """
    if params is None:
        return model_cls()
    if isinstance(params, model_cls):
        return params
    if isinstance(params, BaseModel):
        raise TypeError(
            f"Expected {model_cls.__name__} or a mapping, got {type(params).__name__}"
        )
    return model_cls(**params)


class StartScrapeJobParamsDict(TypedDict, total=False):
    """Parameters for creating a new scrape job."""

    url: Required[str]
    session_options: Union["CreateSessionParamsDict", None]
    scrape_options: Union["ScrapeOptionsDict", None]


class CreateSessionParamsDict(TypedDict, total=False):
    """Parameters for creating a new browser session."""

    use_ultra_stealth: bool
    use_stealth: bool
    use_proxy: bool
    proxy_server: Union[str, None]
    proxy_server_password: Union[str, None]
    proxy_server_username: Union[str, None]
    proxy_country: Union[Country, None]
    proxy_state: Union[State, None]
    proxy_city: Union[str, None]
    operating_systems: Union[List[OperatingSystem], None]
    device: Union[List[Literal["desktop", "mobile"]], None]
    platform: Union[List[Platform], None]
    locales: List[ISO639_1]
    screen: Union["ScreenConfigDict", None]
    solve_captchas: bool
    solver_type: Union[CaptchaSolverType, None]
    adblock: bool
    trackers: bool
    annoyances: bool
    enable_web_recording: Union[bool, None]
    enable_video_web_recording: Union[bool, None]
    enable_log_capture: Union[bool, None]
    profile: Union["CreateSessionProfileDict", None]
    extension_ids: Union[List[str], None]
    static_ip_id: Union[str, None]
    accept_cookies: Union[bool, None]
    url_blocklist: Union[List[str], None]
    browser_args: Union[List[str], None]
    disabled_external_protocols: Union[List[str], None]
    save_downloads: Union[bool, None]
    image_captcha_params: Union[List["ImageCaptchaParamDict"], None]
    timeout_minutes: Union[int, None]
    enable_window_manager: Union[bool, None]
    enable_window_manager_taskbar: Union[bool, None]
    region: Union[SessionRegion, None]
    view_only_live_view: Union[bool, None]
    allow_on_geolocation_prompt: Union[bool, None]
    disable_password_manager: Union[bool, None]
    enable_always_open_pdf_externally: Union[bool, None]
    append_timestamp_to_downloads: Union[bool, None]
    show_scrollbars: Union[bool, None]
    live_view_ttl_seconds: Union[int, None]
    replace_native_elements: Union[bool, None]
    disable_post_quantum_key_agreement: Union[bool, None]
    browser_memory_size: Union[BrowserMemorySize, None]
    start_from_snapshot: Union["StartSessionFromSnapshotParamsDict", None]


class ScreenConfigDict(TypedDict, total=False):
    """Screen configuration parameters for browser session."""

    width: int
    height: int


class CreateSessionProfileDict(TypedDict, total=False):
    """Profile configuration parameters for browser session."""

    id: Union[str, None]
    persist_changes: Union[bool, None]
    persist_network_cache: Union[bool, None]


class ImageCaptchaParamDict(TypedDict, total=False):
    image_selector: Required[str]
    input_selector: Required[str]


class StartSessionFromSnapshotParamsDict(TypedDict, total=False):
    """Snapshot selector for restoring a browser session at creation time."""

    snapshot_id: Required[str]


class ScrapeOptionsDict(TypedDict, total=False):
    """Options for scraping a page."""

    formats: Union[List[ScrapeFormat], None]
    include_tags: Union[List[str], None]
    exclude_tags: Union[List[str], None]
    only_main_content: Union[bool, None]
    wait_for: Union[int, None]
    timeout: Union[int, None]
    wait_until: Union[ScrapeWaitUntil, None]
    screenshot_options: Union["ScreenshotOptionsDict", None]
    storage_state: Union["StorageStateOptionsDict", None]


class ScreenshotOptionsDict(TypedDict, total=False):
    """Options for screenshot."""

    full_page: Union[bool, None]
    format: Union[ScrapeScreenshotFormat, None]
    crop_to_content: Union[bool, None]
    crop_to_content_max_height: Union[int, None]
    crop_to_content_min_height: Union[int, None]
    wait_for: Union[int, None]


class StorageStateOptionsDict(TypedDict, total=False):
    local_storage: Union[Dict[str, str], None]
    session_storage: Union[Dict[str, str], None]


class StartBatchScrapeJobParamsDict(TypedDict, total=False):
    """Parameters for creating a new batch scrape job."""

    urls: Required[List[str]]
    session_options: Union["CreateSessionParamsDict", None]
    scrape_options: Union["ScrapeOptionsDict", None]


class GetBatchScrapeJobParamsDict(TypedDict, total=False):
    """Parameters for getting a batch scrape job."""

    page: Union[int, None]
    batch_size: Union[int, None]


class StartCrawlJobParamsDict(TypedDict, total=False):
    """Parameters for creating a new crawl job."""

    url: Required[str]
    max_pages: Union[int, None]
    follow_links: bool
    ignore_sitemap: bool
    exclude_patterns: List[str]
    include_patterns: List[str]
    session_options: Union["CreateSessionParamsDict", None]
    scrape_options: Union["ScrapeOptionsDict", None]


class GetCrawlJobParamsDict(TypedDict, total=False):
    """Parameters for getting a crawl job."""

    page: Union[int, None]
    batch_size: Union[int, None]


class StartExtractJobParamsDict(TypedDict, total=False):
    """Parameters for creating a new extract job."""

    urls: Required[List[str]]
    system_prompt: Union[str, None]
    prompt: Union[str, None]
    schema: Union[Any, None]
    wait_for: Union[int, None]
    session_options: Union["CreateSessionParamsDict", None]
    max_links: Union[int, None]


class SessionListParamsDict(TypedDict, total=False):
    """Parameters for listing sessions."""

    status: Union[SessionStatus, None]
    page: int
    limit: int


class SessionGetParamsDict(TypedDict, total=False):
    live_view_ttl_seconds: Union[int, None]


class CaptchaEvaluationParamsDict(TypedDict, total=False):
    """Parameters for manually evaluating captchas in a running session."""

    captcha: Union[CaptchaEvaluationType, None]
    captcha_type: Union[CaptchaEvaluationType, None]
    text: Union[CaptchaEvaluationType, None]
    iterations: Union[int, None]
    max_iterations: Union[int, None]
    solver_type: Union[CaptchaSolverType, None]
    image_captcha_params: Union[List["ImageCaptchaParamDict"], None]
    use_gemini_captcha_solver: Union[bool, None]
    use_ultra_stealth: Union[bool, None]


class UpdateSessionProfileParamsDict(TypedDict, total=False):
    """Parameters for updating session profile persistence settings."""

    persist_changes: Union[bool, None]
    persist_network_cache: Union[bool, None]


class UpdateSessionProxyParamsDict(TypedDict, total=False):
    """Parameters for enabling, disabling, or reconfiguring a session proxy."""

    enabled: Required[bool]
    static_ip_id: Union[str, None]
    location: Union["UpdateSessionProxyLocationParamsDict", None]


class UpdateSessionProxyLocationParamsDict(TypedDict, total=False):
    """Managed proxy geolocation overrides for a running session."""

    country: Union[Country, None]
    state: Union[State, None]
    city: Union[str, None]


class UpdateSessionScreenParamsDict(TypedDict, total=False):
    """Parameters for updating the screen size of a running session."""

    width: Required[int]
    height: Required[int]


class UpdateSessionSolveCaptchasParamsDict(TypedDict, total=False):
    """Parameters for starting automatic captcha solving in a running session."""

    solver_type: Union[CaptchaSolverType, None]


class SessionEventLogListParamsDict(TypedDict, total=False):
    page: Union[int, None]
    limit: Union[int, None]
    start_timestamp: Union[int, None]
    end_timestamp: Union[int, None]
    target_id: Union[str, None]
    types: Union[List[SessionEventLogType], None]


class CreateProfileParamsDict(TypedDict, total=False):
    """Parameters for creating a new profile."""

    name: Union[str, None]


class ForkProfileParamsDict(TypedDict, total=False):
    """Parameters for forking an existing profile."""

    name: Union[str, None]


class ProfileListParamsDict(TypedDict, total=False):
    """Parameters for listing profiles."""

    page: int
    limit: int
    name: Union[str, None]


class CreateVolumeParamsDict(TypedDict, total=False):
    name: Required[str]


class CreateExtensionParamsDict(TypedDict, total=False):
    """Parameters for creating a new extension."""

    name: Union[str, None]
    file_path: Required[str]


class FetchParamsDict(TypedDict, total=False):
    url: Required[str]
    stealth: Union[FetchStealthMode, None]
    outputs: Union["FetchOutputOptionsDict", None]
    browser: Union["FetchBrowserOptionsDict", None]
    navigation: Union["FetchNavigationOptionsDict", None]
    cache: Union["FetchCacheOptionsDict", None]


class FetchOutputOptionsDict(TypedDict, total=False):
    formats: Union[List[FetchOutputFormat], None]
    sanitize: Union[FetchSanitizeMode, None]
    include_selectors: Union[List[str], None]
    exclude_selectors: Union[List[str], None]
    storage_state: Union["FetchStorageStateOptionsDict", None]


class FetchOutputMarkdownDict(TypedDict, total=False):
    type: Required[Literal["markdown"]]


class FetchOutputHtmlDict(TypedDict, total=False):
    type: Required[Literal["html"]]


class FetchOutputLinksDict(TypedDict, total=False):
    type: Required[Literal["links"]]


class FetchOutputScreenshotDict(TypedDict, total=False):
    full_page: Union[bool, None]
    format: Union[FetchScreenshotFormat, None]
    crop_to_content: Union[bool, None]
    crop_to_content_max_height: Union[int, None]
    crop_to_content_min_height: Union[int, None]
    type: Required[Literal["screenshot"]]


class FetchOutputJsonDict(TypedDict, total=False):
    prompt: Union[str, None]
    schema: Union[Any, None]
    type: Required[Literal["json"]]


class FetchOutputBrandingDict(TypedDict, total=False):
    type: Required[Literal["branding"]]


class FetchStorageStateOptionsDict(TypedDict, total=False):
    """Storage state to apply before fetching."""

    local_storage: Union[Dict[str, str], None]
    session_storage: Union[Dict[str, str], None]


class FetchBrowserOptionsDict(TypedDict, total=False):
    screen: Union["ScreenConfigDict", None]
    profile_id: Union[str, None]
    solve_captchas: Union[bool, None]
    location: Union["FetchBrowserLocationOptionsDict", None]


class FetchBrowserLocationOptionsDict(TypedDict, total=False):
    country: Union[Country, None]
    state: Union[State, None]
    city: Union[str, None]


class FetchNavigationOptionsDict(TypedDict, total=False):
    wait_until: Union[FetchWaitUntil, None]
    timeout_ms: Union[int, None]
    wait_for: Union[int, None]


class FetchCacheOptionsDict(TypedDict, total=False):
    max_age_seconds: Union[int, None]


class StartBatchFetchJobParamsDict(TypedDict, total=False):
    urls: Required[List[str]]
    stealth: Union[FetchStealthMode, None]
    outputs: Union["FetchOutputOptionsDict", None]
    browser: Union["FetchBrowserOptionsDict", None]
    navigation: Union["FetchNavigationOptionsDict", None]
    cache: Union["FetchCacheOptionsDict", None]


class GetBatchFetchJobParamsDict(TypedDict, total=False):
    page: Union[int, None]
    batch_size: Union[int, None]


class StartWebCrawlJobParamsDict(TypedDict, total=False):
    url: Required[str]
    stealth: Union[FetchStealthMode, None]
    outputs: Union["FetchOutputOptionsDict", None]
    browser: Union["FetchBrowserOptionsDict", None]
    navigation: Union["FetchNavigationOptionsDict", None]
    cache: Union["FetchCacheOptionsDict", None]
    crawl_options: Union["WebCrawlOptionsDict", None]


class WebCrawlOptionsDict(TypedDict, total=False):
    max_pages: Union[int, None]
    ignore_sitemap: Union[bool, None]
    follow_links: Union[bool, None]
    exclude_patterns: Union[List[str], None]
    include_patterns: Union[List[str], None]


class GetWebCrawlJobParamsDict(TypedDict, total=False):
    page: Union[int, None]
    batch_size: Union[int, None]


class WebSearchParamsDict(TypedDict, total=False):
    """Parameters for `/api/web/search`."""

    query: Required[str]
    page: Union[int, None]
    max_age_seconds: Union[int, None]
    location: Union["WebSearchLocationDict", None]
    filters: Union["WebSearchFiltersDict", None]


class WebSearchLocationDict(TypedDict, total=False):
    country: Union[Country, None]
    state: Union[State, None]
    city: Union[str, None]


class WebSearchFiltersDict(TypedDict, total=False):
    """Optional query modifiers applied server-side to the base query.
    Mirrors the server's `/api/web/search` `filters` schema."""

    exact_phrase: Union[bool, None]
    semantic_phrase: Union[bool, None]
    exclude_terms: Union[List[str], None]
    boost_terms: Union[List[str], None]
    filetype: Union[WebSearchFiletype, None]
    site: Union[str, None]
    exclude_site: Union[str, None]
    intitle: Union[str, None]
    inurl: Union[str, None]


class StartBrowserUseTaskParamsDict(TypedDict, total=False):
    """Parameters for creating a new browser use task."""

    task: Required[str]
    version: Union[BrowserUseVersion, None]
    llm: Union[BrowserUseLlm, None]
    session_id: Union[str, None]
    validate_output: Union[bool, None]
    use_vision: Union[bool, None]
    use_vision_for_planner: Union[bool, None]
    max_actions_per_step: Union[int, None]
    max_input_tokens: Union[int, None]
    planner_llm: Union[BrowserUseLlm, None]
    page_extraction_llm: Union[BrowserUseLlm, None]
    planner_interval: Union[int, None]
    max_steps: Union[int, None]
    max_failures: Union[int, None]
    initial_actions: Union[List[Dict[str, Dict[str, Any]]], None]
    sensitive_data: Union[Dict[str, str], None]
    message_context: Union[str, None]
    output_model_schema: Union[Dict[str, Any], Type[BaseModel], None]
    keep_browser_open: Union[bool, None]
    session_options: Union["CreateSessionParamsDict", None]
    use_custom_api_keys: Union[bool, None]
    api_keys: Union["BrowserUseApiKeysDict", None]


class BrowserUseApiKeysDict(TypedDict, total=False):
    """API keys for the browser use task."""

    openai: Union[str, None]
    anthropic: Union[str, None]
    google: Union[str, None]


class StartClaudeComputerUseTaskParamsDict(TypedDict, total=False):
    """Parameters for creating a new Claude Computer Use task."""

    task: Required[str]
    llm: Union[ClaudeComputerUseLlm, None]
    session_id: Union[str, None]
    max_failures: Union[int, None]
    max_steps: Union[int, None]
    keep_browser_open: Union[bool, None]
    session_options: Union["CreateSessionParamsDict", None]
    use_custom_api_keys: Union[bool, None]
    api_keys: Union["ClaudeComputerUseApiKeysDict", None]
    use_computer_action: Union[bool, None]


class ClaudeComputerUseApiKeysDict(TypedDict, total=False):
    """API keys for the Claude Computer Use task."""

    anthropic: Union[str, None]


class StartCuaTaskParamsDict(TypedDict, total=False):
    """Parameters for creating a new CUA task."""

    task: Required[str]
    llm: Union[CuaLlm, None]
    session_id: Union[str, None]
    max_failures: Union[int, None]
    max_steps: Union[int, None]
    keep_browser_open: Union[bool, None]
    session_options: Union["CreateSessionParamsDict", None]
    use_custom_api_keys: Union[bool, None]
    api_keys: Union["CuaApiKeysDict", None]
    use_computer_action: Union[bool, None]


class CuaApiKeysDict(TypedDict, total=False):
    """API keys for the CUA task."""

    openai: Union[str, None]


class StartGeminiComputerUseTaskParamsDict(TypedDict, total=False):
    """Parameters for creating a new Gemini Computer Use task."""

    task: Required[str]
    llm: Union[GeminiComputerUseLlm, None]
    session_id: Union[str, None]
    max_failures: Union[int, None]
    max_steps: Union[int, None]
    keep_browser_open: Union[bool, None]
    session_options: Union["CreateSessionParamsDict", None]
    use_custom_api_keys: Union[bool, None]
    use_computer_action: Union[bool, None]
    api_keys: Union["GeminiComputerUseApiKeysDict", None]


class GeminiComputerUseApiKeysDict(TypedDict, total=False):
    """API keys for the Gemini Computer Use task."""

    google: Union[str, None]


class StartGrokComputerUseTaskParamsDict(TypedDict, total=False):
    """Parameters for creating a new Grok Computer Use task."""

    task: Required[str]
    llm: Union[GrokComputerUseLlm, None]
    reasoning_effort: Union[GrokReasoningEffort, None]
    session_id: Union[str, None]
    max_failures: Union[int, None]
    max_steps: Union[int, None]
    keep_browser_open: Union[bool, None]
    session_options: Union["CreateSessionParamsDict", None]
    use_custom_api_keys: Union[bool, None]
    api_keys: Union["GrokComputerUseApiKeysDict", None]
    use_computer_action: Union[bool, None]


class GrokComputerUseApiKeysDict(TypedDict, total=False):
    """API keys for the Grok Computer Use task."""

    xai: Union[str, None]


class StartHyperAgentTaskParamsDict(TypedDict, total=False):
    """Parameters for creating a new HyperAgent task."""

    version: Union[HyperAgentVersion, None]
    task: Required[str]
    llm: Union[HyperAgentLlm, None]
    session_id: Union[str, None]
    max_steps: Union[int, None]
    enable_visual_mode: Union[bool, None]
    keep_browser_open: Union[bool, None]
    session_options: Union["CreateSessionParamsDict", None]
    use_custom_api_keys: Union[bool, None]
    api_keys: Union["HyperAgentApiKeysDict", None]


class HyperAgentApiKeysDict(TypedDict, total=False):
    """API keys for the HyperAgent task."""

    openai: Union[str, None]
    anthropic: Union[str, None]
    google: Union[str, None]


__all__ = [
    "coerce_to_model",
    "StartScrapeJobParamsDict",
    "CreateSessionParamsDict",
    "ScreenConfigDict",
    "CreateSessionProfileDict",
    "ImageCaptchaParamDict",
    "StartSessionFromSnapshotParamsDict",
    "ScrapeOptionsDict",
    "ScreenshotOptionsDict",
    "StorageStateOptionsDict",
    "StartBatchScrapeJobParamsDict",
    "GetBatchScrapeJobParamsDict",
    "StartCrawlJobParamsDict",
    "GetCrawlJobParamsDict",
    "StartExtractJobParamsDict",
    "SessionListParamsDict",
    "SessionGetParamsDict",
    "CaptchaEvaluationParamsDict",
    "UpdateSessionProfileParamsDict",
    "UpdateSessionProxyParamsDict",
    "UpdateSessionProxyLocationParamsDict",
    "UpdateSessionScreenParamsDict",
    "UpdateSessionSolveCaptchasParamsDict",
    "SessionEventLogListParamsDict",
    "CreateProfileParamsDict",
    "ForkProfileParamsDict",
    "ProfileListParamsDict",
    "CreateVolumeParamsDict",
    "CreateExtensionParamsDict",
    "FetchParamsDict",
    "FetchOutputOptionsDict",
    "FetchOutputMarkdownDict",
    "FetchOutputHtmlDict",
    "FetchOutputLinksDict",
    "FetchOutputScreenshotDict",
    "FetchOutputJsonDict",
    "FetchOutputBrandingDict",
    "FetchStorageStateOptionsDict",
    "FetchBrowserOptionsDict",
    "FetchBrowserLocationOptionsDict",
    "FetchNavigationOptionsDict",
    "FetchCacheOptionsDict",
    "StartBatchFetchJobParamsDict",
    "GetBatchFetchJobParamsDict",
    "StartWebCrawlJobParamsDict",
    "WebCrawlOptionsDict",
    "GetWebCrawlJobParamsDict",
    "WebSearchParamsDict",
    "WebSearchLocationDict",
    "WebSearchFiltersDict",
    "StartBrowserUseTaskParamsDict",
    "BrowserUseApiKeysDict",
    "StartClaudeComputerUseTaskParamsDict",
    "ClaudeComputerUseApiKeysDict",
    "StartCuaTaskParamsDict",
    "CuaApiKeysDict",
    "StartGeminiComputerUseTaskParamsDict",
    "GeminiComputerUseApiKeysDict",
    "StartGrokComputerUseTaskParamsDict",
    "GrokComputerUseApiKeysDict",
    "StartHyperAgentTaskParamsDict",
    "HyperAgentApiKeysDict",
]
