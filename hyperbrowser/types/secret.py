from typing import Dict, List, Literal, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict

from ..customer_key import CustomerKey


class SecretReference(TypedDict, total=False):
    """Selects a stored secret; an omitted version means the latest. A
    customer-protected secret also takes ``unwrapped``, the envelope
    ``secrets.unwrap()`` returns, with ``version`` pinned to the version
    number it was unwrapped from."""

    name: Required[str]
    version: Optional[Union[int, Literal["latest"]]]
    unwrapped: Optional[str]


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
    with the ``op_token`` secret named ``token`` (or, for a
    customer-protected op_token, the reference ``secrets.unwrap()``
    returns)."""

    token: Union[str, SecretReference]
    vault: str
    fields: Dict[str, OnePasswordField]


# What a secret's value is; fixed when the secret is created. "secret" is an
# opaque string, "totp" a TOTP seed (base32 or an otpauth://totp/ URI) and
# "op_token" a 1Password service account token.
SecretType = Literal["secret", "totp", "op_token"]

# Who can open a secret's stored versions: the platform alone, or only with
# the customer's own key as well. Fixed when the secret is created.
SecretProtection = Literal["platform", "customer"]

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
    ``customer_key`` wraps the first version of a customer-protected secret,
    and implies ``protection="customer"``.
    """

    name: Required[str]
    description: Optional[str]
    type: Optional[SecretType]
    protection: Optional[SecretProtection]
    allowed_origins: Optional[List[str]]
    metadata: Optional[SecretMetadata]
    value: Optional[SecretValue]
    customer_key: Optional[CustomerKey]


class UpdateSecretParams(TypedDict, total=False):
    """A new description, metadata members to replace (``None`` removes one),
    or both."""

    description: Optional[str]
    metadata: Optional[SecretMetadata]


class ReplaceSecretVersionWrappingParams(TypedDict):
    """A customer-protected version's new outer envelope; ``inner_digest``
    must be the version's."""

    envelope: str
    inner_digest: str


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
    "ReplaceSecretVersionWrappingParams",
    "SecretBrowserMetadata",
    "SecretListParams",
    "SecretMetadata",
    "SecretProtection",
    "SecretReference",
    "SecretReferenceInput",
    "SecretType",
    "SecretValue",
    "UpdateSecretParams",
]
