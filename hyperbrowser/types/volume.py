from typing_extensions import TypedDict


class CreateVolumeParams(TypedDict):
    """Parameters for creating a persistent sandbox volume."""

    name: str


__all__ = ["CreateVolumeParams"]
