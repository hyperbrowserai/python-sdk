from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateProfileParams(BaseModel):
    """
    Parameters for creating a new profile.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    name: Optional[str] = Field(default=None, serialization_alias="name")


class CreateProfileResponse(BaseModel):
    """
    Response containing the created profile.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    id: str
    name: Optional[str] = Field(default=None)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    id: str
    name: Optional[str] = Field(default=None)
    team_id: str = Field(alias="teamId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ProfileListParams(BaseModel):
    """
    Parameters for listing profiles.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1)
    name: Optional[str] = Field(default=None)


class ProfileListResponse(BaseModel):
    """
    Response containing a list of profiles with pagination information.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    profiles: List[ProfileResponse]
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
