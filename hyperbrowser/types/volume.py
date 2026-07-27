from typing import Optional

from typing_extensions import TypedDict


class CreateVolumeParams(TypedDict):
    """Parameters for creating a persistent sandbox volume."""

    name: str


class VolumeListParams(TypedDict, total=False):
    """Filters and pagination for listing sandbox volumes."""

    page: Optional[int]
    limit: Optional[int]
    search: Optional[str]


__all__ = ["CreateVolumeParams", "VolumeListParams"]
