"""Typed dictionary requests for vaults."""

from typing import Dict, Literal, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict


class StoredEntry(TypedDict, total=False):
    """A stored secret for one variable; an omitted version (or ``"latest"``)
    follows the latest version."""

    name: Required[str]
    version: Optional[Union[int, Literal["latest"]]]


class OnePasswordEntry(TypedDict, total=False):
    """A field of a 1Password item, by name or ID. ``field`` may end with a
    query such as ``?attribute=otp``."""

    item: Required[str]
    section: Optional[str]
    field: Required[str]


VaultEntryInput: TypeAlias = Union[StoredEntry, OnePasswordEntry]


class StoredVaultSource(TypedDict):
    """Values come from the team's stored secrets (the default)."""

    type: Literal["stored"]


class OnePasswordVaultSource(TypedDict):
    """Values come from a 1Password vault, signed in to with the service
    account token in the ``op_token`` secret named ``token_secret``."""

    type: Literal["1password"]
    token_secret: str
    vault: str


VaultSourceInput: TypeAlias = Union[StoredVaultSource, OnePasswordVaultSource]


class OnePasswordSourceUpdate(TypedDict, total=False):
    """New settings for a 1Password vault; members left out are kept."""

    token_secret: Optional[str]
    vault: Optional[str]


class CreateVaultParams(TypedDict, total=False):
    """A new vault: environment variable names mapped to entries."""

    name: Required[str]
    description: Optional[str]
    source: Optional[VaultSourceInput]
    entries: Optional[Dict[str, VaultEntryInput]]


class UpdateVaultParams(TypedDict, total=False):
    """Changes to a vault. An entry set to ``None`` removes that variable."""

    description: Optional[str]
    source: Optional[OnePasswordSourceUpdate]
    entries: Optional[Dict[str, Optional[VaultEntryInput]]]


class VaultListParams(TypedDict, total=False):
    """Filters and pagination for listing vaults."""

    page: Optional[int]
    limit: Optional[int]
    search: Optional[str]


__all__ = [
    "CreateVaultParams",
    "OnePasswordEntry",
    "OnePasswordSourceUpdate",
    "OnePasswordVaultSource",
    "StoredEntry",
    "StoredVaultSource",
    "UpdateVaultParams",
    "VaultEntryInput",
    "VaultListParams",
    "VaultSourceInput",
]
