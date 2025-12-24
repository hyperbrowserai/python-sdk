from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Union
from .common import FetchOutputLike, FetchOptions, FetchSessionOptions
from hyperbrowser.models.consts import FetchStatus


class FetchParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    url: str
    outputs: Optional[List[FetchOutputLike]] = Field(
        default=None, serialization_alias="outputs"
    )
    fetch_options: Optional[FetchOptions] = Field(
        default=None, serialization_alias="fetchOptions"
    )
    session_options: Optional[FetchSessionOptions] = Field(
        default=None, serialization_alias="sessionOptions"
    )


class FetchResponseData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    metadata: Optional[dict[str, Union[str, list[str]]]] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    links: Optional[List[str]] = None
    screenshot: Optional[str] = None
    json_: Optional[dict] = Field(
        default=None, alias="json", serialization_alias="json"
    )


class FetchResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: FetchStatus
    error: Optional[str] = None
    data: Optional[FetchResponseData] = None
