from __future__ import annotations
from typing import Any, Literal, Optional, Union, List
from pydantic import BaseModel, Field, ConfigDict
from hyperbrowser.models.consts import (
    FetchScreenshotFormat,
    FetchWaitUntil,
    PageStatus,
    Country,
    State,
    SessionRegion,
)
from hyperbrowser.models.session import (
    ScreenConfig,
    CreateSessionProfile,
    ImageCaptchaParam,
)


class FetchSessionOptions(BaseModel):
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
    screen: Optional[ScreenConfig] = Field(default=None)
    solve_captchas: bool = Field(default=False, serialization_alias="solveCaptchas")
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
    browser_args: Optional[List[str]] = Field(
        default=None, serialization_alias="browserArgs"
    )
    image_captcha_params: Optional[List[ImageCaptchaParam]] = Field(
        default=None, serialization_alias="imageCaptchaParams"
    )
    region: Optional[SessionRegion] = Field(default=None, serialization_alias="region")


class FetchOutputScreenshotOptions(BaseModel):
    """
    Options for screenshot output.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    full_page: Optional[bool] = Field(default=None, serialization_alias="fullPage")
    format: Optional[FetchScreenshotFormat] = Field(
        default=None, serialization_alias="format"
    )
    crop_to_content: Optional[bool] = Field(
        default=None, serialization_alias="cropToContent"
    )
    crop_to_content_max_height: Optional[int] = Field(
        default=None, serialization_alias="cropToContentMaxHeight"
    )
    crop_to_content_min_height: Optional[int] = Field(
        default=None, serialization_alias="cropToContentMinHeight"
    )
    wait_for: Optional[int] = Field(default=None, serialization_alias="waitFor")


class FetchStorageStateOptions(BaseModel):
    """
    Storage state to apply before fetching.
    """

    local_storage: Optional[dict[str, str]] = Field(
        default=None, serialization_alias="localStorage"
    )
    session_storage: Optional[dict[str, str]] = Field(
        default=None, serialization_alias="sessionStorage"
    )


class FetchOptions(BaseModel):
    """
    Options for fetching a page.
    """

    include_tags: Optional[list[str]] = Field(
        default=None, serialization_alias="includeTags"
    )
    exclude_tags: Optional[list[str]] = Field(
        default=None, serialization_alias="excludeTags"
    )
    sanitize: Optional[bool] = Field(default=None, serialization_alias="sanitize")
    wait_for: Optional[int] = Field(default=None, serialization_alias="waitFor")
    timeout: Optional[int] = Field(default=None, serialization_alias="timeout")
    wait_until: Optional[FetchWaitUntil] = Field(
        default=None, serialization_alias="waitUntil"
    )
    storage_state: Optional[FetchStorageStateOptions] = Field(
        default=None, serialization_alias="storageState"
    )


class PageData(BaseModel):
    """
    Output data for a fetched page.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    status: PageStatus
    error: Optional[str] = None
    metadata: Optional[dict[str, Union[str, list[str]]]] = None
    markdown: Optional[str] = None
    html: Optional[str] = None
    links: Optional[list[str]] = None
    screenshot: Optional[str] = None
    json_: Optional[dict[str, Any]] = Field(
        default=None, alias="json", serialization_alias="json"
    )


class _FetchOutputBase(BaseModel):
    """
    Base class for output descriptors used when requesting outputs.
    """

    options: Optional[dict[str, Any]] = None


class FetchOutputMarkdown(_FetchOutputBase):
    type: Literal["markdown"]


class FetchOutputHtml(_FetchOutputBase):
    type: Literal["html"]


class FetchOutputLinks(_FetchOutputBase):
    type: Literal["links"]


class FetchOutputScreenshot(BaseModel):
    type: Literal["screenshot"]
    options: Optional[FetchOutputScreenshotOptions] = None


class FetchOutputJsonOptions(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    schema_: Optional[Any] = Field(
        default=None, alias="schema", serialization_alias="schema"
    )


class FetchOutputJson(BaseModel):
    type: Literal["json"]
    options: FetchOutputJsonOptions


FetchOutputLike = Union[
    FetchOutputMarkdown,
    FetchOutputHtml,
    FetchOutputLinks,
    FetchOutputScreenshot,
    FetchOutputJson,
    Literal["markdown", "html", "links", "screenshot"],
]
