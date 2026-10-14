"""Vaults: named sets of environment variables whose values come from stored
secrets or from a 1Password vault. A vault holds no values itself."""

import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import ConfigDict, Field, field_validator, model_validator

from .secret import (
    SECRET_ENV_NAME_PATTERN,
    SecretBaseModel,
    validate_secret_name,
    validate_secret_version,
)

MAX_VAULT_ENTRIES = 32
MAX_VAULT_ENV_NAME_LENGTH = 256
MAX_ONEPASSWORD_NAME_LENGTH = 256
MAX_ONEPASSWORD_REFERENCE_BYTES = 512
# Characters 1Password names can't hold in an op:// reference: control,
# format, line separator and paragraph separator characters.
_ONEPASSWORD_FORBIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})


def _utf16_length(value: str) -> int:
    # The server counts string lengths in UTF-16 code units.
    return len(value.encode("utf-16-le", "surrogatepass")) // 2


def _is_query_part(text: str, allowed) -> bool:
    return bool(text) and all(char in allowed for char in text)


_QUERY_KEY_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz-")
_QUERY_VALUE_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
)


def validate_onepassword_name(value: str, what: str, query: bool = False) -> str:
    """Check a 1Password vault, item, section or field name (or ID) for an
    ``op://`` reference. A field may end with a query such as
    ``?attribute=otp``."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty 1Password name or ID")
    if _utf16_length(value) > MAX_ONEPASSWORD_NAME_LENGTH:
        raise ValueError(
            f"{what} is longer than {MAX_ONEPASSWORD_NAME_LENGTH} characters"
        )
    name, _, params = value.partition("?") if query else (value, "", "")
    if query and "?" in value:
        for pair in params.split("&"):
            key, equals, setting = pair.partition("=")
            if not (
                equals
                and _is_query_part(key, _QUERY_KEY_CHARS)
                and _is_query_part(setting, _QUERY_VALUE_CHARS)
            ):
                raise ValueError(
                    f"{what} has an invalid query; expected ?key=value pairs "
                    "such as ?attribute=otp"
                )
    if (
        not name
        or name in (".", "..")
        or "/" in name
        or "?" in name
        or any(
            unicodedata.category(char) in _ONEPASSWORD_FORBIDDEN_CATEGORIES
            for char in name
        )
    ):
        raise ValueError(
            f"{what} must be a 1Password name or ID without '/' or '?', control "
            "characters, or a name of '.' or '..'"
        )
    return value


def validate_vault_env_name(env: Any) -> str:
    if (
        not isinstance(env, str)
        or not SECRET_ENV_NAME_PATTERN.fullmatch(env)
        or len(env) > MAX_VAULT_ENV_NAME_LENGTH
        or env == "__proto__"
    ):
        raise ValueError(
            f"Invalid vault entry name {env!r}: entries are environment variable "
            f"names of up to {MAX_VAULT_ENV_NAME_LENGTH} letters, digits and '_', "
            "not starting with a digit"
        )
    return env


class StoredEntry(SecretBaseModel):
    """A vault entry that takes its value from a stored secret.

    An omitted ``version`` (or ``"latest"``) follows the secret's latest
    version.
    """

    name: str
    version: Optional[Union[int, Literal["latest"]]] = None


class OnePasswordEntry(SecretBaseModel):
    """A vault entry that takes its value from a field of a 1Password item.

    ``item``, ``section`` and ``field`` are names or IDs; ``field`` may end
    with a query such as ``?attribute=otp``. In responses, ``reference`` is
    the ``op://vault/item/[section/]field`` reference the platform resolves.
    """

    item: str
    section: Optional[str] = None
    field: str


VaultEntryInput = Union[StoredEntry, OnePasswordEntry]


class VaultStoredEntry(StoredEntry):
    """A stored entry as the API reports it: ``version`` is ``None`` when it
    follows the latest version."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    secret_id: Optional[str] = Field(default=None, alias="secretId")


class VaultOnePasswordEntry(OnePasswordEntry):
    """A 1Password entry as the API reports it, with the
    ``op://vault/item/[section/]field`` reference the platform resolves."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    reference: Optional[str] = None


VaultEntry = Union[VaultStoredEntry, VaultOnePasswordEntry]


def _parse_entry(value: Any) -> Any:
    if isinstance(value, (StoredEntry, OnePasswordEntry)) or not isinstance(
        value, dict
    ):
        return value
    if "item" in value:
        return OnePasswordEntry.model_validate(value)
    return StoredEntry.model_validate(value)


def _parse_reported_entry(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    if "item" in value:
        return VaultOnePasswordEntry.model_validate(value)
    return VaultStoredEntry.model_validate(value)


class StoredVaultSource(SecretBaseModel):
    """Values come from the team's stored secrets (the default)."""

    type: Literal["stored"]


class OnePasswordVaultSource(SecretBaseModel):
    """Values come from a 1Password vault.

    ``token_secret`` names an ``op_token`` secret holding a 1Password service
    account token; ``vault`` is the 1Password vault's name or ID.
    """

    type: Literal["1password"]
    token_secret: str = Field(serialization_alias="tokenSecret")
    vault: str

    @field_validator("token_secret")
    @classmethod
    def validate_token_secret(cls, value):
        return validate_secret_name(value)

    @field_validator("vault")
    @classmethod
    def validate_vault(cls, value):
        return validate_onepassword_name(value, "The 1Password vault")


VaultSourceInput = Union[StoredVaultSource, OnePasswordVaultSource]


class OnePasswordSourceUpdate(SecretBaseModel):
    """New settings for a 1Password vault; ``None`` keeps a setting."""

    token_secret: Optional[str] = Field(default=None, serialization_alias="tokenSecret")
    vault: Optional[str] = None

    @field_validator("token_secret")
    @classmethod
    def validate_token_secret(cls, value):
        return None if value is None else validate_secret_name(value)

    @field_validator("vault")
    @classmethod
    def validate_vault(cls, value):
        return (
            None
            if value is None
            else validate_onepassword_name(value, "The 1Password vault")
        )

    @model_validator(mode="after")
    def require_a_setting(self):
        if self.token_secret is None and self.vault is None:
            raise ValueError("A source update needs token_secret, vault, or both")
        return self


def _check_entry(env: str, entry: Any) -> None:
    validate_vault_env_name(env)
    if isinstance(entry, StoredEntry):
        validate_secret_name(entry.name)
        if entry.version is not None and entry.version != "latest":
            validate_secret_version(entry.version)
    elif isinstance(entry, OnePasswordEntry):
        validate_onepassword_name(entry.item, f"{env}: item")
        if entry.section is not None:
            validate_onepassword_name(entry.section, f"{env}: section")
        validate_onepassword_name(entry.field, f"{env}: field", query=True)


def onepassword_reference(vault: str, entry: OnePasswordEntry) -> str:
    """The ``op://`` reference the platform builds for an entry."""
    parts = [vault, entry.item] + ([entry.section] if entry.section else [])
    return "op://" + "/".join(parts + [entry.field])


class CreateVaultParams(SecretBaseModel):
    """A new vault.

    ``entries`` maps environment variable names to a :class:`StoredEntry`
    (stored vaults) or a :class:`OnePasswordEntry` (1Password vaults).
    ``source`` is fixed at creation and defaults to stored secrets.
    """

    name: str
    description: Optional[str] = None
    source: Optional[VaultSourceInput] = Field(default=None, discriminator="type")
    entries: Optional[Dict[str, VaultEntryInput]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return validate_secret_name(value)

    @field_validator("entries", mode="before")
    @classmethod
    def parse_entries(cls, value):
        if not isinstance(value, dict):
            return value
        if len(value) > MAX_VAULT_ENTRIES:
            raise ValueError(f"A vault can hold at most {MAX_VAULT_ENTRIES} entries")
        return {env: _parse_entry(entry) for env, entry in value.items()}

    @model_validator(mode="after")
    def check_entries(self):
        onepassword = isinstance(self.source, OnePasswordVaultSource)
        for env, entry in (self.entries or {}).items():
            _check_entry(env, entry)
            if onepassword != isinstance(entry, OnePasswordEntry):
                raise ValueError(
                    f"{env}: a {'1Password' if onepassword else 'stored'} vault "
                    f"takes {'OnePasswordEntry' if onepassword else 'StoredEntry'} "
                    "entries"
                )
            if isinstance(self.source, OnePasswordVaultSource) and isinstance(
                entry, OnePasswordEntry
            ):
                reference = onepassword_reference(self.source.vault, entry)
                if len(reference.encode("utf-8")) > MAX_ONEPASSWORD_REFERENCE_BYTES:
                    raise ValueError(
                        f"{env}: the 1Password reference is longer than "
                        f"{MAX_ONEPASSWORD_REFERENCE_BYTES} bytes"
                    )
        return self


class UpdateVaultParams(SecretBaseModel):
    """Changes to a vault. Members left out (or ``None``) are kept.

    Each entry given replaces that variable, and an entry set to ``None``
    removes it. ``source`` changes a 1Password vault's token secret or
    1Password vault; a vault's source type can't change.
    """

    description: Optional[str] = None
    source: Optional[OnePasswordSourceUpdate] = None
    entries: Optional[Dict[str, Optional[VaultEntryInput]]] = None

    @field_validator("entries", mode="before")
    @classmethod
    def parse_entries(cls, value):
        if not isinstance(value, dict):
            return value
        return {env: _parse_entry(entry) for env, entry in value.items()}

    @model_validator(mode="after")
    def check_changes(self):
        if self.description is None and self.source is None and self.entries is None:
            raise ValueError("Update a vault's description, source, entries, or more")
        for env, entry in (self.entries or {}).items():
            _check_entry(env, entry)
        return self


class VaultListParams(SecretBaseModel):
    page: Optional[int] = Field(default=None, ge=1)
    limit: Optional[int] = Field(default=None, ge=1, le=100)
    search: Optional[str] = None


class VaultTokenSecret(SecretBaseModel):
    """The ``op_token`` secret a 1Password vault signs in with."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str
    secret_id: Optional[str] = Field(default=None, alias="secretId")


class VaultSource(SecretBaseModel):
    """Where a vault's values come from.

    ``type`` is ``"stored"`` or ``"1password"``; it is kept as a string so
    sources the API adds later still parse. 1Password vaults set
    ``token_secret`` and ``vault``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: str = "stored"
    token_secret: Optional[VaultTokenSecret] = Field(default=None, alias="tokenSecret")
    vault: Optional[str] = None


class Vault(SecretBaseModel):
    id: str
    name: str
    description: str = ""
    # APIs without 1Password vaults leave it out: the vault is stored.
    source: VaultSource = Field(default_factory=VaultSource)
    entries: Dict[str, VaultEntry] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    @field_validator("description", mode="before")
    @classmethod
    def default_description(cls, value):
        return "" if value is None else value

    @field_validator("source", mode="before")
    @classmethod
    def default_source(cls, value):
        return {"type": "stored"} if value is None else value

    @field_validator("entries", mode="before")
    @classmethod
    def parse_entries(cls, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            return value
        return {env: _parse_reported_entry(entry) for env, entry in value.items()}


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
    "OnePasswordEntry",
    "OnePasswordSourceUpdate",
    "OnePasswordVaultSource",
    "StoredEntry",
    "StoredVaultSource",
    "UpdateVaultParams",
    "Vault",
    "VaultDeleteResult",
    "VaultEntry",
    "VaultEntryInput",
    "VaultListParams",
    "VaultListResponse",
    "VaultOnePasswordEntry",
    "VaultSource",
    "VaultSourceInput",
    "VaultStoredEntry",
    "VaultTokenSecret",
]
