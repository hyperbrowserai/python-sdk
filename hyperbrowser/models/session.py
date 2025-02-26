from datetime import datetime
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hyperbrowser.models.consts import (
    ISO639_1,
    Country,
    DownloadsStatus,
    OperatingSystem,
    Platform,
    RecordingStatus,
    State,
)

SessionStatus = Literal["active", "closed", "error"]


class BasicResponse(BaseModel):
    """
    Represents a basic Hyperbrowser response.
    """

    success: bool


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
    live_url: str = Field(alias="liveUrl")
    token: str = Field(alias="token")


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


class ScreenConfig(BaseModel):
    """
    Screen configuration parameters for browser session.
    """

    width: int = Field(default=1280, serialization_alias="width")
    height: int = Field(default=720, serialization_alias="height")


class CreateSessionProfile(BaseModel):
    """
    Profile configuration parameters for browser session.
    """

    id: Optional[str] = Field(default=None, serialization_alias="id")
    persist_changes: Optional[bool] = Field(
        default=None, serialization_alias="persistChanges"
    )


class CreateSessionParams(BaseModel):
    """
    Parameters for creating a new browser session.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
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
    adblock: bool = Field(default=False, serialization_alias="adblock")
    trackers: bool = Field(default=False, serialization_alias="trackers")
    annoyances: bool = Field(default=False, serialization_alias="annoyances")
    enable_web_recording: Optional[bool] = Field(
        default=True, serialization_alias="enableWebRecording"
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
