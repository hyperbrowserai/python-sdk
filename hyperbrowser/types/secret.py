from typing import Dict, List, Literal, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict


class SecretReference(TypedDict, total=False):
    """Selects a stored secret; an omitted version means the latest."""

    name: Required[str]
    version: Optional[Union[int, Literal["latest"]]]


# A plain secret name is shorthand for {"name": name}.
SecretReferenceInput: TypeAlias = Union[str, SecretReference]


class OnePasswordField(TypedDict, total=False):
    """A field of an item in the request's 1Password vault, by name or ID.
    ``field`` may end with a query such as ``?attribute=totp``."""

    item: Required[str]
    section: Optional[str]
    field: Required[str]


class OnePasswordSource(TypedDict):
    """Environment variables from fields of one 1Password vault, signed in to
    with the ``op_token`` secret named ``token``."""

    token: str
    vault: str
    fields: Dict[str, OnePasswordField]


# What a secret's value is; fixed when the secret is created. "secret" is an
# opaque string, "totp" a TOTP seed (base32 or an otpauth://totp/ URI) and
# "op_token" a 1Password service account token.
SecretType = Literal["secret", "totp", "op_token"]

# A secret value, encrypted locally before upload.
SecretValue: TypeAlias = Union[str, bytes]


class SecretBrowserMetadata(TypedDict):
    """Origins (``scheme://host[:port]``, ``*.`` for subdomains) a secret may
    be typed into browser pages on."""

    allowed_origins: List[str]


class SecretMetadata(TypedDict, total=False):
    """Secret metadata. In an update, ``None`` removes a member."""

    browser: Optional[SecretBrowserMetadata]


class CreateSecretParams(TypedDict, total=False):
    """Parameters for creating a secret, optionally with its first value.

    ``allowed_origins`` is shorthand for ``metadata.browser.allowed_origins``;
    it makes a ``secret`` or ``totp`` fillable in browser sessions.
    """

    name: Required[str]
    description: Optional[str]
    type: Optional[SecretType]
    allowed_origins: Optional[List[str]]
    metadata: Optional[SecretMetadata]
    value: Optional[SecretValue]


class UpdateSecretParams(TypedDict, total=False):
    """A new description, metadata members to replace (``None`` removes one),
    or both."""

    description: Optional[str]
    metadata: Optional[SecretMetadata]


class SecretListParams(TypedDict, total=False):
    """Filters and pagination for listing secrets."""

    page: Optional[int]
    limit: Optional[int]
    search: Optional[str]
    type: Optional[SecretType]


__all__ = [
    "CreateSecretParams",
    "OnePasswordField",
    "OnePasswordSource",
    "SecretBrowserMetadata",
    "SecretListParams",
    "SecretMetadata",
    "SecretReference",
    "SecretReferenceInput",
    "SecretType",
    "SecretValue",
    "UpdateSecretParams",
]
