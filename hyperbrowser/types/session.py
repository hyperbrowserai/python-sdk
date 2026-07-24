from typing import List, Literal, Optional

from typing_extensions import Required, TypedDict

from hyperbrowser.models.consts import (
    Country,
    ISO639_1,
    OperatingSystem,
    Platform,
    SessionEventLogType,
    SessionRegion,
    State,
)


SessionStatus = Literal["active", "closed", "error"]
BrowserMemorySize = Literal["small", "medium", "large"]
CaptchaSolverType = Literal["visual"]
CaptchaEvaluationType = Literal[
    "turnstile",
    "cloudflare-challenge",
    "aliexpress",
    "recaptcha",
    "recaptcha-visual",
    "amazon",
]
CaptchaEvaluationTarget = CaptchaEvaluationType
BrowserDevice = Literal["desktop", "mobile"]


class ScreenConfig(TypedDict, total=False):
    """Browser viewport dimensions in pixels."""

    width: int
    height: int


class UpdateSessionProfileParams(TypedDict, total=False):
    """Profile persistence settings for a running session."""

    persist_changes: Optional[bool]
    persist_network_cache: Optional[bool]


class UpdateSessionProxyLocationParams(TypedDict, total=False):
    """Geographic proxy location for a running session."""

    country: Optional[Country]
    state: Optional[State]
    city: Optional[str]


class UpdateSessionProxyParams(TypedDict, total=False):
    """Proxy settings to apply to a running session."""

    enabled: Required[bool]
    static_ip_id: Optional[str]
    location: Optional[UpdateSessionProxyLocationParams]


class UpdateSessionScreenParams(TypedDict):
    """Viewport dimensions to apply to a running session."""

    width: int
    height: int


class SessionGetParams(TypedDict, total=False):
    """Optional parameters for retrieving a browser session."""

    live_view_ttl_seconds: Optional[int]


class SessionListParams(TypedDict, total=False):
    """Filters and pagination for listing browser sessions."""

    status: Optional[SessionStatus]
    page: int
    limit: int


class CreateSessionProfile(TypedDict, total=False):
    """Profile configuration for a new browser session."""

    id: Optional[str]
    persist_changes: Optional[bool]
    persist_network_cache: Optional[bool]


class ImageCaptchaParam(TypedDict):
    """Selectors describing an image CAPTCHA challenge."""

    image_selector: str
    input_selector: str


class CaptchaEvaluationParams(TypedDict, total=False):
    """Parameters for manually evaluating CAPTCHA solving."""

    captcha: Optional[CaptchaEvaluationType]
    captcha_type: Optional[CaptchaEvaluationType]
    text: Optional[CaptchaEvaluationType]
    iterations: Optional[int]
    max_iterations: Optional[int]
    solver_type: Optional[CaptchaSolverType]
    image_captcha_params: Optional[List[ImageCaptchaParam]]
    use_gemini_captcha_solver: Optional[bool]
    use_ultra_stealth: Optional[bool]


class StartSessionFromSnapshotParams(TypedDict):
    """Snapshot to restore when creating a browser session."""

    snapshot_id: str


class CreateSessionParams(TypedDict, total=False):
    """Configuration for creating a browser session."""

    use_ultra_stealth: bool
    use_stealth: bool
    use_proxy: bool
    proxy_server: Optional[str]
    proxy_server_password: Optional[str]
    proxy_server_username: Optional[str]
    proxy_country: Optional[Country]
    proxy_state: Optional[State]
    proxy_city: Optional[str]
    operating_systems: Optional[List[OperatingSystem]]
    device: Optional[List[BrowserDevice]]
    platform: Optional[List[Platform]]
    locales: List[ISO639_1]
    screen: Optional[ScreenConfig]
    solve_captchas: bool
    solver_type: Optional[CaptchaSolverType]
    adblock: bool
    trackers: bool
    annoyances: bool
    enable_web_recording: Optional[bool]
    enable_video_web_recording: Optional[bool]
    enable_log_capture: Optional[bool]
    profile: Optional[CreateSessionProfile]
    extension_ids: Optional[List[str]]
    static_ip_id: Optional[str]
    accept_cookies: Optional[bool]
    url_blocklist: Optional[List[str]]
    browser_args: Optional[List[str]]
    disabled_external_protocols: Optional[List[str]]
    save_downloads: Optional[bool]
    image_captcha_params: Optional[List[ImageCaptchaParam]]
    timeout_minutes: Optional[int]
    enable_window_manager: Optional[bool]
    enable_window_manager_taskbar: Optional[bool]
    region: Optional[SessionRegion]
    view_only_live_view: Optional[bool]
    allow_on_geolocation_prompt: Optional[bool]
    disable_password_manager: Optional[bool]
    enable_always_open_pdf_externally: Optional[bool]
    append_timestamp_to_downloads: Optional[bool]
    show_scrollbars: Optional[bool]
    live_view_ttl_seconds: Optional[int]
    replace_native_elements: Optional[bool]
    disable_post_quantum_key_agreement: Optional[bool]
    browser_memory_size: Optional[BrowserMemorySize]
    start_from_snapshot: Optional[StartSessionFromSnapshotParams]


class UpdateSessionSolveCaptchasParams(TypedDict, total=False):
    """CAPTCHA solver settings for a running session."""

    solver_type: Optional[CaptchaSolverType]


class SessionEventLogListParams(TypedDict, total=False):
    """Filters and pagination for session event logs."""

    page: Optional[int]
    limit: Optional[int]
    start_timestamp: Optional[int]
    end_timestamp: Optional[int]
    target_id: Optional[str]
    types: Optional[List[SessionEventLogType]]


__all__ = [
    "BrowserDevice",
    "BrowserMemorySize",
    "CaptchaEvaluationParams",
    "CaptchaEvaluationTarget",
    "CaptchaEvaluationType",
    "CaptchaSolverType",
    "CreateSessionParams",
    "CreateSessionProfile",
    "ImageCaptchaParam",
    "ScreenConfig",
    "SessionEventLogListParams",
    "SessionGetParams",
    "SessionListParams",
    "SessionStatus",
    "StartSessionFromSnapshotParams",
    "UpdateSessionProfileParams",
    "UpdateSessionProxyLocationParams",
    "UpdateSessionProxyParams",
    "UpdateSessionScreenParams",
    "UpdateSessionSolveCaptchasParams",
]
