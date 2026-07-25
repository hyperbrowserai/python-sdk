from typing import Optional

from typing_extensions import TypedDict


class CreateProfileParams(TypedDict, total=False):
    """Parameters for creating a browser profile."""

    name: Optional[str]


class ForkProfileParams(TypedDict, total=False):
    """Parameters for forking a browser profile."""

    name: Optional[str]


class ProfileListParams(TypedDict, total=False):
    """Filters and pagination for listing browser profiles."""

    page: int
    limit: int
    name: Optional[str]


__all__ = ["CreateProfileParams", "ForkProfileParams", "ProfileListParams"]
