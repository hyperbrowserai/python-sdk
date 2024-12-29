from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class CreateContextResponse(BaseModel):
    id: str


class ContextResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    id: str
    team_id: str = Field(alias="teamId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
