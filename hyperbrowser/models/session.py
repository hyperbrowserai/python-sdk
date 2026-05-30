from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hyperbrowser.models.consts import (
    ISO639_1,
    Country,
    DownloadsStatus,
    OperatingSystem,
    Platform,
    RecordingStatus,
    State,
    SessionRegion,
    SessionEventLogType,
)

SessionStatus = Literal["active", "closed", "error"]
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


class BasicResponse(BaseModel):
    """
    Represents a basic Hyperbrowser response.
    """

    success: bool


class ScreenConfig(BaseModel):
    """
    Screen configuration parameters for browser session.
    """

    width: int = Field(default=1280, serialization_alias="width")
    height: int = Field(default=720, serialization_alias="height")


class SessionProfile(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    id: str = Field(alias="id")
    persist_changes: Optional[bool] = Field(
        default=None, alias="persistChanges", serialization_alias="persistChanges"
    )
    persist_network_cache: Optional[bool] = Field(
        default=None,
        alias="persistNetworkCache",
        serialization_alias="persistNetworkCache",
    )


class UpdateSessionProfileParams(BaseModel):
    """
    Parameters for updating session profile persistence settings.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    persist_changes: Optional[bool] = Field(
        default=None, serialization_alias="persistChanges"
    )
    persist_network_cache: Optional[bool] = Field(
        default=None,
        serialization_alias="persistNetworkCache",
    )


class UpdateSessionProxyLocationParams(BaseModel):
    """
    Managed proxy geolocation overrides for a running session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    country: Optional[Country] = Field(default=None, serialization_alias="country")
    state: Optional[State] = Field(default=None, serialization_alias="state")
    city: Optional[str] = Field(default=None, serialization_alias="city")


class UpdateSessionProxyParams(BaseModel):
    """
    Parameters for enabling, disabling, or reconfiguring a session proxy.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    enabled: bool = Field(serialization_alias="enabled")
    static_ip_id: Optional[str] = Field(default=None, serialization_alias="staticIpId")
    location: Optional[UpdateSessionProxyLocationParams] = Field(
        default=None,
        serialization_alias="location",
    )


class UpdateSessionScreenParams(BaseModel):
    """
    Parameters for updating the screen size of a running session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    width: int = Field(serialization_alias="width")
    height: int = Field(serialization_alias="height")


class SessionLaunchState(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    use_ultra_stealth: Optional[bool] = Field(default=None, alias="useUltraStealth")
    use_stealth: Optional[bool] = Field(default=None, alias="useStealth")
    use_proxy: Optional[bool] = Field(default=None, alias="useProxy")
    solve_captchas: Optional[bool] = Field(default=None, alias="solveCaptchas")
    adblock: Optional[bool] = Field(default=None, alias="adblock")
    trackers: Optional[bool] = Field(default=None, alias="trackers")
    annoyances: Optional[bool] = Field(default=None, alias="annoyances")
    screen: Optional[ScreenConfig] = Field(default=None, alias="screen")
    enable_web_recording: Optional[bool] = Field(
        default=None, alias="enableWebRecording"
    )
    enable_video_web_recording: Optional[bool] = Field(
        default=None, alias="enableVideoWebRecording"
    )
    enable_log_capture: Optional[bool] = Field(default=None, alias="enableLogCapture")
    accept_cookies: Optional[bool] = Field(default=None, alias="acceptCookies")
    solver_type: Optional[CaptchaSolverType] = Field(default=None, alias="solverType")
    profile: Optional[SessionProfile] = Field(default=None, alias="profile")
    static_ip_id: Optional[str] = Field(default=None, alias="staticIpId")
    save_downloads: Optional[bool] = Field(default=None, alias="saveDownloads")
    enable_window_manager: Optional[bool] = Field(
        default=None, alias="enableWindowManager"
    )
    enable_window_manager_taskbar: Optional[bool] = Field(
        default=None, alias="enableWindowManagerTaskbar"
    )
    view_only_live_view: Optional[bool] = Field(default=None, alias="viewOnlyLiveView")
    allow_on_geolocation_prompt: Optional[bool] = Field(
        default=None, alias="allowOnGeolocationPrompt"
    )
    disable_password_manager: Optional[bool] = Field(
        default=None, alias="disablePasswordManager"
    )
    enable_always_open_pdf_externally: Optional[bool] = Field(
        default=None, alias="enableAlwaysOpenPdfExternally"
    )
    append_timestamp_to_downloads: Optional[bool] = Field(
        default=None, alias="appendTimestampToDownloads"
    )
    disable_post_quantum_key_agreement: Optional[bool] = Field(
        default=None, alias="disablePostQuantumKeyAgreement"
    )


class SessionCreditBreakdown(BaseModel):
    """
    Breakdown of credits used by a session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    credits_used: Optional[float] = Field(default=None, alias="creditsUsed")
    browser_time_credits_used: Optional[float] = Field(
        default=None, alias="browserTimeCreditsUsed"
    )
    proxy_data_credits_used: Optional[float] = Field(
        default=None, alias="proxyDataCreditsUsed"
    )


class Session(BaseModel):
    """
    Represents a basic session in the Hyperbrowser system.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    id: str
    team_id: str = Field(alias="teamId")
    status: SessionStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    start_time: Optional[int] = Field(default=None, alias="startTime")
    end_time: Optional[int] = Field(default=None, alias="endTime")
    duration: Optional[int] = None
    session_url: str = Field(alias="sessionUrl")
    proxy_data_consumed: str = Field(alias="proxyDataConsumed")
    launch_state: Optional[SessionLaunchState] = Field(
        default=None, alias="launchState"
    )
    credits_used: Optional[float] = Field(default=None, alias="creditsUsed")
    credit_breakdown: Optional[SessionCreditBreakdown] = Field(
        default=None, alias="creditBreakdown"
    )

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Optional[Union[str, int]]) -> Optional[int]:
        """Convert string timestamps to integers."""
        if value is None:
            return None
        if isinstance(value, str):
            return int(value)
        return value


class SessionDetail(Session):
    """
    Detailed session information including websocket endpoint.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    ws_endpoint: Optional[str] = Field(alias="wsEndpoint", default=None)
    computer_action_endpoint: Optional[str] = Field(
        alias="computerActionEndpoint", default=None
    )
    webdriver_endpoint: Optional[str] = Field(alias="webdriverEndpoint", default=None)
    live_url: str = Field(alias="liveUrl")
    token: str = Field(alias="token")
    forked_profile_id: Optional[str] = Field(
        default=None, alias="forkedProfileId"
    )


class SessionGetParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    live_view_ttl_seconds: Optional[int] = Field(
        default=None, serialization_alias="liveViewTtlSeconds"
    )


class SessionListParams(BaseModel):
    """
    Parameters for listing sessions.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: Optional[SessionStatus] = Field(default=None, exclude=None)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1)


class SessionListResponse(BaseModel):
    """
    Response containing a list of sessions with pagination information.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    sessions: List[Session]
    total_count: int = Field(alias="totalCount")
    page: int
    per_page: int = Field(alias="perPage")

    @property
    def has_more(self) -> bool:
        """Check if there are more pages available."""
        return self.total_count > (self.page * self.per_page)

    @property
    def total_pages(self) -> int:
        """Calculate the total number of pages."""
        return -(-self.total_count // self.per_page)


class CreateSessionProfile(BaseModel):
    """
    Profile configuration parameters for browser session.
    """

    id: Optional[str] = Field(default=None, serialization_alias="id")
    persist_changes: Optional[bool] = Field(
        default=None, serialization_alias="persistChanges"
    )
    persist_network_cache: Optional[bool] = Field(
        default=None, serialization_alias="persistNetworkCache"
    )
    fork: Optional[bool] = Field(default=None, serialization_alias="fork")
    fork_profile_name: Optional[str] = Field(
        default=None, serialization_alias="forkProfileName"
    )


class ImageCaptchaParam(BaseModel):
    image_selector: str = Field(serialization_alias="imageSelector")
    input_selector: str = Field(serialization_alias="inputSelector")


class CaptchaEvaluationParams(BaseModel):
    """
    Parameters for manually evaluating captchas in a running session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    captcha: Optional[CaptchaEvaluationTarget] = Field(default=None)
    captcha_type: Optional[CaptchaEvaluationTarget] = Field(
        default=None, serialization_alias="captchaType"
    )
    text: Optional[CaptchaEvaluationTarget] = Field(default=None)
    iterations: Optional[int] = Field(default=None)
    max_iterations: Optional[int] = Field(
        default=None, serialization_alias="maxIterations"
    )
    solver_type: Optional[CaptchaSolverType] = Field(
        default=None, serialization_alias="solverType"
    )
    image_captcha_params: Optional[List[ImageCaptchaParam]] = Field(
        default=None, serialization_alias="imageCaptchaParams"
    )
    use_gemini_captcha_solver: Optional[bool] = Field(
        default=None, serialization_alias="useGeminiCaptchaSolver"
    )
    use_ultra_stealth: Optional[bool] = Field(
        default=None, serialization_alias="useUltraStealth"
    )


class CaptchaEvaluationPageResult(BaseModel):
    """
    Result of manually evaluating captchas on a single page target.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str = Field(alias="url")
    target_id: Optional[str] = Field(default=None, alias="targetId")
    iterations_run: int = Field(alias="iterationsRun")
    solved: bool = Field(alias="solved")
    solved_captchas: List[CaptchaEvaluationType] = Field(alias="solvedCaptchas")
    checked_captchas: List[CaptchaEvaluationType] = Field(alias="checkedCaptchas")
    captcha_solved_counts: Dict[str, int] = Field(alias="captchaSolvedCounts")
    last_solve_time: Dict[str, float] = Field(alias="lastSolveTime")


class CaptchaEvaluationResponse(BaseModel):
    """
    Response from manually evaluating captchas in a running session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    success: bool = Field(alias="success")
    captcha: Optional[CaptchaEvaluationType] = Field(default=None, alias="captcha")
    iterations_requested: int = Field(alias="iterationsRequested")
    iterations_run: int = Field(alias="iterationsRun")
    solved: bool = Field(alias="solved")
    solved_captchas: List[CaptchaEvaluationType] = Field(alias="solvedCaptchas")
    pages: List[CaptchaEvaluationPageResult] = Field(alias="pages")


class CreateSessionParams(BaseModel):
    """
    Parameters for creating a new browser session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    use_ultra_stealth: bool = Field(
        default=False, serialization_alias="useUltraStealth"
    )
    use_stealth: bool = Field(default=False, serialization_alias="useStealth")
    use_proxy: bool = Field(default=False, serialization_alias="useProxy")
    proxy_server: Optional[str] = Field(default=None, serialization_alias="proxyServer")
    proxy_server_password: Optional[str] = Field(
        default=None, serialization_alias="proxyServerPassword"
    )
    proxy_server_username: Optional[str] = Field(
        default=None, serialization_alias="proxyServerUsername"
    )
    proxy_country: Optional[Country] = Field(
        default=None, serialization_alias="proxyCountry"
    )
    proxy_state: Optional[State] = Field(default=None, serialization_alias="proxyState")
    proxy_city: Optional[str] = Field(default=None, serialization_alias="proxyCity")
    operating_systems: Optional[List[OperatingSystem]] = Field(
        default=None, serialization_alias="operatingSystems"
    )
    device: Optional[List[Literal["desktop", "mobile"]]] = Field(default=None)
    platform: Optional[List[Platform]] = Field(default=None)
    locales: List[ISO639_1] = Field(default=["en"])
    screen: Optional[ScreenConfig] = Field(default=None)
    solve_captchas: bool = Field(default=False, serialization_alias="solveCaptchas")
    solver_type: Optional[CaptchaSolverType] = Field(
        default=None, serialization_alias="solverType"
    )
    adblock: bool = Field(default=False, serialization_alias="adblock")
    trackers: bool = Field(default=False, serialization_alias="trackers")
    annoyances: bool = Field(default=False, serialization_alias="annoyances")
    enable_web_recording: Optional[bool] = Field(
        default=None, serialization_alias="enableWebRecording"
    )
    enable_video_web_recording: Optional[bool] = Field(
        default=None, serialization_alias="enableVideoWebRecording"
    )
    enable_log_capture: Optional[bool] = Field(
        default=None, serialization_alias="enableLogCapture"
    )
    profile: Optional[CreateSessionProfile] = Field(default=None)
    extension_ids: Optional[List[str]] = Field(
        default=None, serialization_alias="extensionIds"
    )
    static_ip_id: Optional[str] = Field(default=None, serialization_alias="staticIpId")
    accept_cookies: Optional[bool] = Field(
        default=None, serialization_alias="acceptCookies"
    )
    url_blocklist: Optional[List[str]] = Field(
        default=None, serialization_alias="urlBlocklist"
    )
    browser_args: Optional[List[str]] = Field(
        default=None, serialization_alias="browserArgs"
    )
    save_downloads: Optional[bool] = Field(
        default=None, serialization_alias="saveDownloads"
    )
    image_captcha_params: Optional[List[ImageCaptchaParam]] = Field(
        default=None, serialization_alias="imageCaptchaParams"
    )
    timeout_minutes: Optional[int] = Field(
        default=None, serialization_alias="timeoutMinutes"
    )
    enable_window_manager: Optional[bool] = Field(
        default=None, serialization_alias="enableWindowManager"
    )
    enable_window_manager_taskbar: Optional[bool] = Field(
        default=None, serialization_alias="enableWindowManagerTaskbar"
    )
    region: Optional[SessionRegion] = Field(default=None, serialization_alias="region")
    view_only_live_view: Optional[bool] = Field(
        default=None, serialization_alias="viewOnlyLiveView"
    )
    allow_on_geolocation_prompt: Optional[bool] = Field(
        default=None, serialization_alias="allowOnGeolocationPrompt"
    )
    disable_password_manager: Optional[bool] = Field(
        default=None, serialization_alias="disablePasswordManager"
    )
    enable_always_open_pdf_externally: Optional[bool] = Field(
        default=None, serialization_alias="enableAlwaysOpenPdfExternally"
    )
    append_timestamp_to_downloads: Optional[bool] = Field(
        default=None, serialization_alias="appendTimestampToDownloads"
    )
    show_scrollbars: Optional[bool] = Field(
        default=None, serialization_alias="showScrollbars"
    )
    live_view_ttl_seconds: Optional[int] = Field(
        default=None, serialization_alias="liveViewTtlSeconds"
    )
    replace_native_elements: Optional[bool] = Field(
        default=None,
        serialization_alias="replaceNativeElements",
    )
    """This option replaces native elements (say for dropdowns) with a custom dropdown.
    Use this option with caution, as this may cause unusual behavior in the browser.
    """
    disable_post_quantum_key_agreement: Optional[bool] = Field(
        default=None, serialization_alias="disablePostQuantumKeyAgreement"
    )


class SessionRecording(BaseModel):
    """
    Model for session recording data.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    type: int
    data: Any
    timestamp: int
    delay: Optional[int] = None


class GetSessionRecordingUrlResponse(BaseModel):
    """
    Response containing the signed URL for the session recording.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: RecordingStatus = Field(alias="status")
    recording_url: Optional[str] = Field(default=None, alias="recordingUrl")
    error: Optional[str] = Field(default=None, alias="error")


class GetSessionVideoRecordingUrlResponse(BaseModel):
    """
    Response containing the signed URL for the session video recording.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: RecordingStatus = Field(alias="status")
    recording_url: Optional[str] = Field(default=None, alias="recordingUrl")
    error: Optional[str] = Field(default=None, alias="error")


class GetSessionDownloadsUrlResponse(BaseModel):
    """
    Response containing the signed URL for the session downloads.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: DownloadsStatus = Field(alias="status")
    downloads_url: Optional[str] = Field(default=None, alias="downloadsUrl")
    error: Optional[str] = Field(default=None, alias="error")


class UploadFileResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    message: str = Field(alias="message")
    file_path: Optional[str] = Field(default=None, alias="filePath")
    file_name: Optional[str] = Field(default=None, alias="fileName")
    original_name: Optional[str] = Field(default=None, alias="originalName")


class UpdateSessionSolveCaptchasParams(BaseModel):
    """
    Parameters for starting automatic captcha solving in a running session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    solver_type: Optional[CaptchaSolverType] = Field(
        default=None,
        serialization_alias="solverType",
    )


class UpdateSessionSolveCaptchasResponse(BasicResponse):
    """
    Response from updating automatic captcha solving in a running session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    solve_captchas: Optional[bool] = Field(default=None, alias="solveCaptchas")
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    telemetry_ready: Optional[bool] = Field(default=None, alias="telemetryReady")


class SessionEventLog(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    id: str = Field(alias="id")
    session_id: str = Field(alias="sessionId")
    target_id: Optional[str] = Field(alias="targetId")
    page_url: Optional[str] = Field(alias="pageUrl")
    team_id: str = Field(alias="teamId")
    type: SessionEventLogType = Field(alias="type")
    metadata: Dict[str, Any] = Field(alias="metadata")
    timestamp: int = Field(alias="timestamp")


class SessionEventLogListParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    page: Optional[int] = Field(default=None, serialization_alias="page")
    limit: Optional[int] = Field(default=None, serialization_alias="limit")
    start_timestamp: Optional[int] = Field(
        default=None, serialization_alias="startTimestamp"
    )
    end_timestamp: Optional[int] = Field(
        default=None, serialization_alias="endTimestamp"
    )
    target_id: Optional[str] = Field(default=None, serialization_alias="targetId")
    types: Optional[List[SessionEventLogType]] = Field(
        default=None, serialization_alias="types"
    )


class SessionEventLogListResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    data: List[SessionEventLog] = Field(alias="data")
    total_count: int = Field(alias="totalCount")
    page: int = Field(alias="page")
    per_page: int = Field(alias="perPage")
