import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# The server's rules for secret names, the environment variables secrets are
# delivered to, and version numbers.
SECRET_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")
SECRET_ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_SECRET_VERSION = 2**31 - 1
MAX_SECRET_BINDINGS = 32
MAX_SECRET_ENV_NAME_LENGTH = 256
# The longest unwrapped envelope the API takes.
MAX_UNWRAPPED_ENVELOPE_LENGTH = 64 * 1024


def validate_secret_name(name: str) -> str:
    if not SECRET_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            f"Invalid secret name {name!r}: names are 1-128 letters, digits, "
            "'_' or '-', starting with a letter or digit"
        )
    return name


def validate_secret_version(version: int) -> int:
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or not 1 <= version <= MAX_SECRET_VERSION
    ):
        raise ValueError(
            f"Invalid secret version {version!r}: expected 1 to {MAX_SECRET_VERSION}"
        )
    return version


def validate_unwrapped_envelope(value, what: str = "the secret"):
    if value is not None and (
        not isinstance(value, str)
        or not 1 <= len(value) <= MAX_UNWRAPPED_ENVELOPE_LENGTH
    ):
        raise ValueError(
            f"The unwrapped envelope of {what} must be a string of 1 to "
            f"{MAX_UNWRAPPED_ENVELOPE_LENGTH} characters"
        )
    return value


class SecretBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SecretReference(SecretBaseModel):
    """Selects a stored secret for an environment variable.

    An omitted version (or ``"latest"``) means the latest version. A
    customer-protected secret also takes ``unwrapped``, the envelope
    ``secrets.unwrap()`` returns, and then ``version`` must be the version
    number it was unwrapped from.
    """

    name: str
    version: Optional[Union[int, Literal["latest"]]] = None
    unwrapped: Optional[str] = Field(default=None, repr=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return validate_secret_name(value)

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, value):
        if value is not None and value != "latest":
            validate_secret_version(value)
        return value

    @field_validator("unwrapped", mode="plain")
    @classmethod
    def validate_unwrapped(cls, value):
        return validate_unwrapped_envelope(value)

    @model_validator(mode="after")
    def require_pinned_version(self):
        # An unwrapped envelope is one version's value; "latest" could move on.
        if self.unwrapped is not None and not isinstance(self.version, int):
            raise ValueError(
                f"Pin the version of secret {self.name} to the version you "
                'unwrapped when passing "unwrapped"'
            )
        return self


SecretReferenceInput = Union[str, SecretReference]


def normalize_secret_references(value):
    """Accept a plain secret name as shorthand for ``{"name": name}``, and
    check the environment variable names."""
    if not isinstance(value, dict):
        return value
    if not value:
        return None
    if len(value) > MAX_SECRET_BINDINGS:
        raise ValueError(
            f"At most {MAX_SECRET_BINDINGS} secrets can be delivered at once"
        )
    for env in value:
        validate_secret_env_name(env)
    return {
        env: {"name": reference} if isinstance(reference, str) else reference
        for env, reference in value.items()
    }


def validate_secret_env_name(env, what: str = "a secret") -> str:
    if (
        not isinstance(env, str)
        or not SECRET_ENV_NAME_PATTERN.fullmatch(env)
        or len(env) > MAX_SECRET_ENV_NAME_LENGTH
        or env == "__proto__"
    ):
        raise ValueError(
            f"Invalid environment variable name {env!r} for {what}: expected "
            f"up to {MAX_SECRET_ENV_NAME_LENGTH} letters, digits and '_', not "
            "starting with a digit"
        )
    return env


class OnePasswordField(SecretBaseModel):
    """A field of an item in the request's 1Password vault.

    ``item``, ``section`` and ``field`` are names or IDs; ``field`` may end
    with a query such as ``?attribute=otp`` or ``?attribute=totp``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    item: str
    section: Optional[str] = None
    field: str


class OnePasswordSource(SecretBaseModel):
    """Environment variables read from one 1Password vault at process start.

    The API validates names, reference sizes, limits and source conflicts.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    # The op_token secret's name, or for a customer-protected op_token the
    # reference ``secrets.unwrap()`` returns.
    token: Union[str, SecretReference]
    vault: str
    fields: Dict[str, OnePasswordField]


# What a secret's value is; fixed when the secret is created.
#   secret    an opaque string: an environment variable, and typed into pages
#             on its allowed origins
#   totp      a TOTP seed (base32 or an otpauth://totp/ URI): delivered and
#             typed as the code that is current at the time
#   op_token  a 1Password service account token, used only to sign in for
#             one_password fields
SecretType = Literal["secret", "totp", "op_token"]

# Who can open a secret's stored versions; fixed when the secret is created.
#   platform  the platform alone (the default)
#   customer  only with the customer's own key as well: each version is
#             wrapped with it, and each use passes the unwrapped envelope
SecretProtection = Literal["platform", "customer"]

# A secret value, encrypted locally before upload.
SecretValue = Union[str, bytes]


class SecretBrowserMetadata(SecretBaseModel):
    """Where a secret may be typed into browser pages.

    Origins are ``scheme://host[:port]``; a leading ``*.`` matches any
    subdomain. The server normalizes and checks them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    allowed_origins: List[str] = Field(alias="allowedOrigins")


class SecretMetadata(SecretBaseModel):
    """Metadata stored with a secret. ``browser`` makes it fillable.

    Members the SDK doesn't know are kept. In an update, each member sent
    replaces the stored one and ``None`` removes it.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    browser: Optional[SecretBrowserMetadata] = None


def _check_secret_value_shape(value):
    # Contents are checked by the secrets manager, which knows the secret's
    # type; this only keeps unusable types out of the request model.
    if value is None or isinstance(value, (str, bytes)):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    raise ValueError("secret value must be str or bytes")


class CreateSecretParams(SecretBaseModel):
    """A new secret, optionally with its first value.

    ``allowed_origins`` is shorthand for
    ``metadata={"browser": {"allowed_origins": [...]}}``.
    """

    model_config = ConfigDict(populate_by_name=True, hide_input_in_errors=True)

    name: str
    description: Optional[str] = None
    # Omitted means "secret".
    type: Optional[SecretType] = None
    metadata: Optional[SecretMetadata] = None
    # Omitted means "platform", or "customer" when customer_key is given.
    protection: Optional[SecretProtection] = None
    allowed_origins: Optional[List[str]] = Field(default=None, exclude=True)
    # Encrypted locally and uploaded as the first version; never sent as is.
    value: Optional[SecretValue] = Field(default=None, exclude=True, repr=False)
    # A CustomerKey that wraps the first version of a customer-protected
    # secret; never sent.
    customer_key: Optional[Any] = Field(default=None, exclude=True, repr=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return validate_secret_name(value)

    @field_validator("value", mode="plain")
    @classmethod
    def validate_value(cls, value):
        return _check_secret_value_shape(value)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def validate_allowed_origins(cls, value):
        if isinstance(value, (str, bytes)):
            raise ValueError(
                'allowed_origins must be a list of origins such as ["https://example.com"]'
            )
        return value

    @model_validator(mode="after")
    def merge_allowed_origins(self):
        if self.allowed_origins is not None:
            if self.metadata is not None and self.metadata.browser is not None:
                raise ValueError("Pass allowed_origins or metadata.browser, not both")
            metadata = self.metadata or SecretMetadata()
            self.metadata = metadata.model_copy(
                update={
                    "browser": SecretBrowserMetadata(
                        allowed_origins=list(self.allowed_origins)
                    )
                }
            )
        return self


class UpdateSecretParams(SecretBaseModel):
    """A description, metadata, or both.

    Metadata is merged by top-level member: each member sent replaces the
    stored one, ``None`` removes it, and members not sent are kept.
    """

    description: Optional[str] = None
    metadata: Optional[SecretMetadata] = None

    @model_validator(mode="after")
    def require_a_change(self):
        if self.description is None and self.metadata is None:
            raise ValueError("Update a secret's description, metadata, or both")
        return self


class SecretListParams(SecretBaseModel):
    page: Optional[int] = Field(default=None, ge=1)
    limit: Optional[int] = Field(default=None, ge=1, le=100)
    search: Optional[str] = None
    type: Optional[SecretType] = None


class SecretJWK(SecretBaseModel):
    kty: str
    n: str
    e: str


class SecretsPublicKey(SecretBaseModel):
    kid: str
    alg: str
    enc: str
    jwk: SecretJWK


class Secret(SecretBaseModel):
    id: str
    name: str
    description: str = ""
    # One of SecretType; kept as str so types the API adds later still parse.
    type: str = "secret"
    metadata: SecretMetadata = Field(default_factory=SecretMetadata)
    # One of SecretProtection; kept as str like ``type``.
    protection: str = "platform"
    encryption_context: str = Field(alias="encryptionContext")
    latest_version: Optional[int] = Field(default=None, alias="latestVersion")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    @field_validator("type", "metadata", "protection", mode="before")
    @classmethod
    def default_when_null(cls, value, info):
        if value is not None:
            return value
        return {"type": "secret", "protection": "platform"}.get(info.field_name, {})


class SecretVersion(SecretBaseModel):
    version: int
    # The platform key the value is sealed to.
    kid: str
    # The customer key that wrapped a customer-protected version.
    outer_kid: Optional[str] = Field(default=None, alias="outerKid")
    # When the platform key retires; a retired version can't be used.
    retires_at: Optional[datetime] = Field(default=None, alias="retiresAt")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")


class WrappedSecretVersion(SecretBaseModel):
    """A customer-protected version as stored: ``envelope`` is the inner
    envelope (sealed to the platform key ``kid``) wrapped with the customer
    key ``outer_kid``, and ``inner_digest`` identifies the inner envelope."""

    version: int
    kid: str
    retires_at: Optional[datetime] = Field(default=None, alias="retiresAt")
    outer_kid: str = Field(alias="outerKid")
    inner_digest: str = Field(alias="innerDigest")
    envelope: str = Field(repr=False)


class SecretDetail(Secret):
    versions: List[SecretVersion] = Field(default_factory=list)


class SecretListResponse(SecretBaseModel):
    secrets: List[Secret]
    total_count: Optional[int] = Field(default=None, alias="totalCount")
    page: Optional[int] = None
    per_page: Optional[int] = Field(default=None, alias="perPage")


class SecretDeleteResult(SecretBaseModel):
    deleted: bool
    id: Optional[str] = None
    name: Optional[str] = None


class SecretVersionDeleteResult(SecretBaseModel):
    deleted: bool
    version: int


class ReplaceSecretVersionWrappingParams(SecretBaseModel):
    """A customer-protected version's new outer envelope. ``inner_digest``
    must be the version's: only the wrapping changes, never the value."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    envelope: str = Field(min_length=1, repr=False)
    inner_digest: str = Field(min_length=1, serialization_alias="innerDigest")


class SecretBindingSource(SecretBaseModel):
    """Where a delivered variable came from: ``type`` is ``"vault"`` (with the
    vault's ``name``), ``"secrets"`` (the request's own ``secrets``) or
    ``"onePassword"`` (the request's ``one_password``)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: str
    name: Optional[str] = None


class SandboxResolvedSecret(SecretBaseModel):
    """What a process environment variable received; never its value.

    A stored secret sets ``name``, ``secret_id`` and ``version``, and
    ``secret_type="totp"`` when the variable holds the code current at
    process start. A ``one_password`` field sets ``reference`` (its
    ``op://`` reference) and ``token_secret`` (the name of the op_token
    secret used to sign in) instead, and never overrides another source.
    ``source`` is where the variable came from, and ``overrides`` lists
    earlier sources it replaced.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    env: str
    name: Optional[str] = None
    secret_id: Optional[str] = Field(default=None, alias="secretId")
    version: Optional[int] = None
    secret_type: Optional[str] = Field(default=None, alias="secretType")
    reference: Optional[str] = None
    token_secret: Optional[str] = Field(default=None, alias="tokenSecret")
    source: Optional[SecretBindingSource] = None
    overrides: List[SecretBindingSource] = Field(default_factory=list)

    @field_validator("overrides", mode="before")
    @classmethod
    def default_overrides(cls, value):
        return [] if value is None else value
