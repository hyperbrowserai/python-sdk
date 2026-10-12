from typing import Literal, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict


class SecretReference(TypedDict, total=False):
    """Selects a stored secret; an omitted version means the latest."""

    name: Required[str]
    version: Optional[Union[int, Literal["latest"]]]


# A plain secret name is shorthand for {"name": name}.
SecretReferenceInput: TypeAlias = Union[str, SecretReference]


class CreateSecretParams(TypedDict, total=False):
    """Parameters for creating a secret, optionally with its first value."""

    name: Required[str]
    description: Optional[str]
    value: Optional[Union[str, bytes]]


class UpdateSecretParams(TypedDict):
    """Parameters for updating a secret's description."""

    description: str


class SecretListParams(TypedDict, total=False):
    """Filters and pagination for listing secrets."""

    page: Optional[int]
    limit: Optional[int]
    search: Optional[str]


__all__ = [
    "CreateSecretParams",
    "SecretListParams",
    "SecretReference",
    "SecretReferenceInput",
    "UpdateSecretParams",
]
