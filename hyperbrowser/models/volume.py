from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._parsers import _parse_optional_int


class VolumeBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CreateVolumeParams(VolumeBaseModel):
    name: str


class Volume(VolumeBaseModel):
    id: str
    name: str
    size: Optional[int] = None
    transfer_amount: Optional[int] = Field(default=None, alias="transferAmount")

    @field_validator("size", "transfer_amount", mode="before")
    @classmethod
    def parse_optional_int_fields(cls, value):
        return _parse_optional_int(value)


class VolumeListResponse(VolumeBaseModel):
    volumes: List[Volume]
