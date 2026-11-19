from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional
from .common import (
    FetchOutputOptions,
    FetchBrowserOptions,
    FetchNavigationOptions,
    FetchCacheOptions,
)
from .branding import BrandingProfile
from hyperbrowser.models.consts import FetchStatus, FetchStealthMode


class FetchParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    stealth: Optional[FetchStealthMode] = Field(
        default=None, serialization_alias="stealth"
    )
    outputs: Optional[FetchOutputOptions] = Field(
        default=None, serialization_alias="outputs"
    )
    browser: Optional[FetchBrowserOptions] = Field(
        default=None, serialization_alias="browser"
    )
    navigation: Optional[FetchNavigationOptions] = Field(
        default=None, serialization_alias="navigation"
    )
    cache: Optional[FetchCacheOptions] = Field(
        default=None, serialization_alias="cache"
    )


class FetchResponseData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    metadata: Optional[Dict[str, Any]] = None
    # HTTP status of the page the content came from. None when the browser
    # received no response.
    status_code: Optional[int] = Field(default=None, alias="statusCode")
    # URL the page ended on after redirects. For a document such as a PDF, the
    # URL of the downloaded file.
    final_url: Optional[str] = Field(default=None, alias="finalUrl")
    html: Optional[str] = None
    markdown: Optional[str] = None
    links: Optional[List[str]] = None
    screenshot: Optional[str] = None
    json_: Optional[dict] = Field(
        default=None, alias="json", serialization_alias="json"
    )
    branding: Optional[BrandingProfile] = None


class FetchResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: FetchStatus
    error: Optional[str] = None
    data: Optional[FetchResponseData] = None
