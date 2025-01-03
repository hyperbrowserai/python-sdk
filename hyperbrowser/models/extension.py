from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateExtensionParams(BaseModel):
    """
    Parameters for creating a new extension.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    name: Optional[str] = Field(default=None, serialization_alias="name")
    file_path: str = Field(serialization_alias="filePath")


class ExtensionResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    id: str = Field(serialization_alias="id")
    name: str = Field(serialization_alias="name")
    created_at: datetime = Field(serialization_alias="createdAt", alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt", alias="updatedAt")
