"""Typed dictionary requests for vaults."""

from typing import Dict, Literal, Optional, Union

from typing_extensions import Required, TypedDict


class StoredEntry(TypedDict, total=False):
    """A stored secret for one variable; an omitted version (or ``"latest"``)
    follows the latest version."""

    name: Required[str]
    version: Optional[Union[int, Literal["latest"]]]


class CreateVaultParams(TypedDict, total=False):
    """A new vault: environment variable names mapped to stored secrets."""

    name: Required[str]
    description: Optional[str]
    entries: Optional[Dict[str, StoredEntry]]


class UpdateVaultParams(TypedDict, total=False):
    """Changes to a vault. An entry set to ``None`` removes that variable."""

    description: Optional[str]
    entries: Optional[Dict[str, Optional[StoredEntry]]]


class VaultListParams(TypedDict, total=False):
    """Filters and pagination for listing vaults."""

    page: Optional[int]
    limit: Optional[int]
    search: Optional[str]


__all__ = [
    "CreateVaultParams",
    "StoredEntry",
    "UpdateVaultParams",
    "VaultListParams",
]
