from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from hyperbrowser.models.consts import Country, State, WebSearchStatus

WebSearchFiletype = Literal["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "html"]


class WebSearchFilters(BaseModel):
    """
    Optional query modifiers applied server-side to the base query.
    Mirrors the server's `/api/web/search` `filters` schema.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    exact_phrase: Optional[bool] = Field(default=None, serialization_alias="exactPhrase")
    semantic_phrase: Optional[bool] = Field(
        default=None, serialization_alias="semanticPhrase"
    )
    exclude_terms: Optional[List[str]] = Field(
        default=None, serialization_alias="excludeTerms"
    )
    boost_terms: Optional[List[str]] = Field(default=None, serialization_alias="boostTerms")
    filetype: Optional[WebSearchFiletype] = Field(default=None, serialization_alias="filetype")
    site: Optional[str] = Field(default=None, serialization_alias="site")
    exclude_site: Optional[str] = Field(default=None, serialization_alias="excludeSite")
    intitle: Optional[str] = Field(default=None, serialization_alias="intitle")
    inurl: Optional[str] = Field(default=None, serialization_alias="inurl")


class WebSearchRegion(BaseModel):
    """
    Region proxy tuple accepted by `/api/web/search`.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    country: Country
    state: Optional[State] = None
    city: Optional[str] = None


class WebSearchParams(BaseModel):
    """
    Parameters for `/api/web/search`.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    query: str
    page: Optional[int] = Field(default=None, serialization_alias="page")
    max_age_seconds: Optional[int] = Field(
        default=None, serialization_alias="maxAgeSeconds"
    )
    region: Optional[WebSearchRegion] = None
    filters: Optional[WebSearchFilters] = None


class WebSearchResultItem(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    title: str
    url: str
    description: str


class WebSearchResponseData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    query: str
    results: List[WebSearchResultItem]


class WebSearchResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
        extra="ignore",
    )

    status: WebSearchStatus
    error: Optional[str] = None
    data: Optional[WebSearchResponseData] = None


