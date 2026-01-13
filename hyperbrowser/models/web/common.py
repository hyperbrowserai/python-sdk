from __future__ import annotations
from typing import Any, Literal, Optional, Union, List
from pydantic import BaseModel, Field, ConfigDict
from hyperbrowser.models.consts import (
    FetchScreenshotFormat,
    FetchWaitUntil,
    PageStatus,
    Country,
    State,
)
from hyperbrowser.models.session import ScreenConfig


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


class FetchBrowserLocationOptions(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    country: Optional[Country] = Field(default=None, serialization_alias="country")
    state: Optional[State] = Field(default=None, serialization_alias="state")
    city: Optional[str] = Field(default=None, serialization_alias="city")


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


class FetchOutputMarkdown(BaseModel):
    type: Literal["markdown"]


class FetchOutputHtml(BaseModel):
    type: Literal["html"]


class FetchOutputLinks(BaseModel):
    type: Literal["links"]


class FetchOutputScreenshot(FetchOutputScreenshotOptions):
    type: Literal["screenshot"]


class FetchOutputJsonOptions(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    schema_: Optional[Any] = Field(
        default=None, alias="schema", serialization_alias="schema"
    )


class FetchOutputJson(FetchOutputJsonOptions):
    type: Literal["json"]


FetchOutputFormat = Union[
    FetchOutputMarkdown,
    FetchOutputHtml,
    FetchOutputLinks,
    FetchOutputScreenshot,
    FetchOutputJson,
    Literal["markdown", "html", "links", "screenshot"],
]


class FetchOutputOptions(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    formats: Optional[List[FetchOutputFormat]] = Field(
        default=None, serialization_alias="formats"
    )
    sanitize: Optional[bool] = Field(default=None, serialization_alias="sanitize")
    include_selectors: Optional[List[str]] = Field(
        default=None, serialization_alias="includeSelectors"
    )
    exclude_selectors: Optional[List[str]] = Field(
        default=None, serialization_alias="excludeSelectors"
    )
    storage_state: Optional[FetchStorageStateOptions] = Field(
        default=None, serialization_alias="storageState"
    )


class FetchBrowserOptions(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    screen: Optional[ScreenConfig] = Field(default=None, serialization_alias="screen")
    profile_id: Optional[str] = Field(default=None, serialization_alias="profileId")
    solve_captchas: Optional[str] = Field(
        default=None, serialization_alias="solveCaptchas"
    )
    location: Optional[FetchBrowserLocationOptions] = Field(
        default=None, serialization_alias="location"
    )


class FetchNavigationOptions(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    wait_until: Optional[FetchWaitUntil] = Field(
        default=None, serialization_alias="waitUntil"
    )
    timeout_ms: Optional[int] = Field(default=None, serialization_alias="timeoutMs")
    wait_for: Optional[int] = Field(default=None, serialization_alias="waitFor")


class FetchCacheOptions(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    max_age_seconds: Optional[int] = Field(
        default=None, serialization_alias="maxAgeSeconds"
    )
