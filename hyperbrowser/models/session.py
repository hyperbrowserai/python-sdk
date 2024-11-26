from typing import List, Literal, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

SessionStatus = Literal["active", "closed", "error"]

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

    @field_validator('start_time', 'end_time', mode='before')
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
    websocket_url: Optional[str] = Field(alias="wsEndpoint", default=None)

class SessionListParams(BaseModel):
    """
    Parameters for listing sessions.
    """
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: Optional[SessionStatus] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(alias="perPage", default=20, ge=1, le=100)

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