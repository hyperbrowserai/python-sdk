from typing import Optional

from typing_extensions import Required, TypedDict


class CreateExtensionParams(TypedDict, total=False):
    """Parameters for uploading a browser extension archive."""

    name: Optional[str]
    file_path: Required[str]


__all__ = ["CreateExtensionParams"]
