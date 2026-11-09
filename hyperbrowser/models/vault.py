"""Vaults: named sets of environment variables whose values come from stored
secrets. A vault holds no values itself."""

from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from pydantic import ConfigDict, Field, field_validator

from .secret import (
    MAX_SECRET_BINDINGS,
    SecretBaseModel,
    WrappedSecretVersion,
    validate_secret_env_name,
    validate_secret_name,
    validate_secret_version,
    validate_unwrapped_envelope,
)


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
    # The secret's protection: a "customer" entry is used through the
    # reference ``vaults.unwrap()`` returns.
    protection: Optional[str] = None


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


class WrappedVaultEntry(WrappedSecretVersion):
    """A customer-protected entry's wrapped envelope: the version of secret
    ``name`` the entry resolves to now."""

    name: str
    secret_id: str = Field(alias="secretId")


class WrappedVault(SecretBaseModel):
    """A vault's customer-protected entries, wrapped; other entries are
    left out."""

    id: str
    name: str
    entries: Dict[str, WrappedVaultEntry] = Field(default_factory=dict)

    @field_validator("entries", mode="before")
    @classmethod
    def default_entries(cls, value):
        return {} if value is None else value


class VaultUnwrappedEntry(SecretBaseModel):
    """One customer-protected entry, unwrapped: the version it was unwrapped
    from and its envelope, which only the platform can open."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    version: int
    unwrapped: str = Field(repr=False)

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, value):
        return validate_secret_version(value)

    @field_validator("unwrapped", mode="plain")
    @classmethod
    def validate_unwrapped(cls, value):
        if value is None:
            raise ValueError("unwrapped is required")
        return validate_unwrapped_envelope(value, "the vault entry")


class VaultReference(SecretBaseModel):
    """A vault with its customer-protected entries unwrapped, as
    ``vaults.unwrap()`` returns it. Pass it as a sandbox's or process's
    ``vault``; entries that aren't customer-protected are delivered as
    usual."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str
    unwrapped: Dict[str, VaultUnwrappedEntry]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return validate_secret_name(value)

    @field_validator("unwrapped", mode="before")
    @classmethod
    def validate_entries(cls, value):
        if isinstance(value, dict):
            if len(value) > MAX_SECRET_BINDINGS:
                raise ValueError(
                    f"At most {MAX_SECRET_BINDINGS} unwrapped vault entries are allowed"
                )
            for env in value:
                validate_secret_env_name(env, "a vault entry")
        return value


__all__ = [
    "CreateVaultParams",
    "StoredEntry",
    "UpdateVaultParams",
    "Vault",
    "VaultDeleteResult",
    "VaultEntry",
    "VaultListParams",
    "VaultListResponse",
    "VaultReference",
    "VaultUnwrappedEntry",
    "WrappedVault",
    "WrappedVaultEntry",
]
