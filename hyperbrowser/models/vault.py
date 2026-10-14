"""Vaults: named sets of environment variables whose values come from stored
secrets. A vault holds no values itself."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import ConfigDict, Field, field_validator, model_validator

from .secret import (
    MAX_SECRET_ENV_NAME_LENGTH,
    SecretBaseModel,
    validate_secret_env_name,
    validate_secret_name,
    validate_secret_version,
)

MAX_VAULT_ENTRIES = 32
MAX_VAULT_ENV_NAME_LENGTH = MAX_SECRET_ENV_NAME_LENGTH


def validate_vault_env_name(env: Any) -> str:
    return validate_secret_env_name(env, "a vault entry")


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


def _check_entry(env: str, entry: Optional[StoredEntry]) -> None:
    validate_vault_env_name(env)
    if entry is None:
        return
    validate_secret_name(entry.name)
    if entry.version is not None and entry.version != "latest":
        validate_secret_version(entry.version)


class CreateVaultParams(SecretBaseModel):
    """A new vault: ``entries`` maps environment variable names to the
    stored secrets they take."""

    # Strict like the API: a member it doesn't take, such as a removed
    # ``source``, is refused instead of dropped.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str
    description: Optional[str] = None
    entries: Optional[Dict[str, StoredEntry]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return validate_secret_name(value)

    @field_validator("entries", mode="before")
    @classmethod
    def limit_entries(cls, value):
        if isinstance(value, dict) and len(value) > MAX_VAULT_ENTRIES:
            raise ValueError(f"A vault can hold at most {MAX_VAULT_ENTRIES} entries")
        return value

    @model_validator(mode="after")
    def check_entries(self):
        for env, entry in (self.entries or {}).items():
            _check_entry(env, entry)
        return self


class UpdateVaultParams(SecretBaseModel):
    """Changes to a vault. Members left out (or ``None``) are kept.

    Each entry given replaces that variable, and an entry set to ``None``
    removes it.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    description: Optional[str] = None
    entries: Optional[Dict[str, Optional[StoredEntry]]] = None

    @model_validator(mode="after")
    def check_changes(self):
        if self.description is None and self.entries is None:
            raise ValueError("Update a vault's description, entries, or both")
        for env, entry in (self.entries or {}).items():
            _check_entry(env, entry)
        return self


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
