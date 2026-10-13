from typing import List, Literal, Mapping, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict


class SecretReference(TypedDict, total=False):
    """Selects a stored secret; an omitted version means the latest."""

    name: Required[str]
    version: Optional[Union[int, Literal["latest"]]]


# A plain secret name is shorthand for {"name": name}.
SecretReferenceInput: TypeAlias = Union[str, SecretReference]


# A plain secret holds one string; a credential holds a website login that
# browser sessions fill into pages. Fixed when the secret is created.
SecretType = Literal["secret", "credential"]

# str or bytes for a plain secret; a mapping of field names (such as
# "username" and "password") to strings for a credential.
SecretValue: TypeAlias = Union[str, bytes, Mapping[str, str]]


class CredentialBrowserMetadata(TypedDict):
    """Origins (``scheme://host[:port]``, ``*.`` for subdomains) a credential
    may be filled on."""

    allowed_origins: List[str]


class SecretMetadata(TypedDict, total=False):
    """Secret metadata. In an update, ``None`` removes a member."""

    browser: Optional[CredentialBrowserMetadata]


class CreateSecretParams(TypedDict, total=False):
    """Parameters for creating a secret, optionally with its first value."""

    name: Required[str]
    description: Optional[str]
    type: Optional[SecretType]
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
    "CredentialBrowserMetadata",
    "SecretListParams",
    "SecretMetadata",
    "SecretReference",
    "SecretReferenceInput",
    "SecretType",
    "SecretValue",
    "UpdateSecretParams",
]
