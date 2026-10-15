"""Vaults: named sets of environment variables whose values come from stored
secrets. A vault holds no values itself."""

from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from pydantic import ConfigDict, Field, field_validator

from .secret import SecretBaseModel


class StoredEntry(SecretBaseModel):
    """A vault entry that takes its value from a stored secret.

    An omitted ``version`` (or ``"latest"``) follows the secret's latest
    version.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str
    version: Optional[Union[int, Literal["latest"]]] = None


class VaultEntry(StoredEntry):
    """An entry as the API reports it: ``version`` is ``None`` when it
    follows the latest version."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    secret_id: Optional[str] = Field(default=None, alias="secretId")


class CreateVaultParams(SecretBaseModel):
    """A new vault: ``entries`` maps environment variable names to the
    stored secrets they take."""

    # Strict like the API: a member it doesn't take, such as a removed
    # ``source``, is refused instead of dropped.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str
    description: Optional[str] = None
    entries: Optional[Dict[str, StoredEntry]] = None


class UpdateVaultParams(SecretBaseModel):
    """Changes to a vault. Members left out (or ``None``) are kept.

    Each entry given replaces that variable, and an entry set to ``None``
    removes it.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    description: Optional[str] = None
    entries: Optional[Dict[str, Optional[StoredEntry]]] = None


class VaultListParams(SecretBaseModel):
    page: Optional[int] = Field(default=None, ge=1)
    limit: Optional[int] = Field(default=None, ge=1, le=100)
    search: Optional[str] = None


class Vault(SecretBaseModel):
    id: str
    name: str
    description: str = ""
    entries: Dict[str, VaultEntry] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    @field_validator("description", mode="before")
    @classmethod
    def default_description(cls, value):
        return "" if value is None else value

    @field_validator("entries", mode="before")
    @classmethod
    def default_entries(cls, value):
        return {} if value is None else value


class VaultListResponse(SecretBaseModel):
    vaults: List[Vault]
    total_count: Optional[int] = Field(default=None, alias="totalCount")
    page: Optional[int] = None
    per_page: Optional[int] = Field(default=None, alias="perPage")


class VaultDeleteResult(SecretBaseModel):
    deleted: bool
    id: Optional[str] = None
    name: Optional[str] = None


__all__ = [
    "CreateVaultParams",
    "StoredEntry",
    "UpdateVaultParams",
    "Vault",
    "VaultDeleteResult",
    "VaultEntry",
    "VaultListParams",
    "VaultListResponse",
]
