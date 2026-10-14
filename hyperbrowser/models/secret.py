import ipaddress
import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# The server's rules for secret names, the environment variables secrets are
# delivered to, and version numbers.
SECRET_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")
SECRET_ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_SECRET_VERSION = 2**31 - 1
MAX_SECRET_BINDINGS = 32
MAX_SECRET_ENV_NAME_LENGTH = 256


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


class SecretBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SecretReference(SecretBaseModel):
    """Selects a stored secret for an environment variable.

    An omitted version (or ``"latest"``) means the latest version.
    """

    name: str
    version: Optional[Union[int, Literal["latest"]]] = None

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
        if (
            not isinstance(env, str)
            or not SECRET_ENV_NAME_PATTERN.fullmatch(env)
            or env == "__proto__"
        ):
            raise ValueError(
                f"Invalid environment variable name {env!r} for a secret: "
                "expected letters, digits and '_', not starting with a digit"
            )
    return {
        env: {"name": reference} if isinstance(reference, str) else reference
        for env, reference in value.items()
    }


MAX_ONEPASSWORD_NAME_LENGTH = 256
MAX_ONEPASSWORD_REFERENCE_BYTES = 512
# Characters 1Password names can't hold in an op:// reference: control,
# format, line separator and paragraph separator characters.
_ONEPASSWORD_FORBIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})
# A field may end with a query, such as ?attribute=otp or ?ssh-format=openssh.
_ONEPASSWORD_QUERY_PATTERN = re.compile(
    r"\?[a-z-]+=[A-Za-z0-9_-]+(?:&[a-z-]+=[A-Za-z0-9_-]+)*"
)


def _utf16_length(value: str) -> int:
    # The server counts string lengths in UTF-16 code units.
    return len(value.encode("utf-16-le", "surrogatepass")) // 2


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
    name, mark, params = value.partition("?") if query else (value, "", "")
    if mark and not _ONEPASSWORD_QUERY_PATTERN.fullmatch(mark + params):
        raise ValueError(
            f"{what} has an invalid query; expected ?key=value pairs such as "
            "?attribute=otp"
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

    @field_validator("item")
    @classmethod
    def validate_item(cls, value):
        return validate_onepassword_name(value, "item")

    @field_validator("section")
    @classmethod
    def validate_section(cls, value):
        return None if value is None else validate_onepassword_name(value, "section")

    @field_validator("field")
    @classmethod
    def validate_field(cls, value):
        return validate_onepassword_name(value, "field", query=True)


def onepassword_reference(vault: str, field: OnePasswordField) -> str:
    """The ``op://vault/item/[section/]field`` reference the platform builds."""
    parts = [vault, field.item] + ([field.section] if field.section else [])
    return "op://" + "/".join(parts + [field.field])


class OnePasswordSource(SecretBaseModel):
    """Environment variables from fields of one 1Password vault.

    ``token`` names an ``op_token`` secret holding a 1Password service account
    token (its latest version signs in); ``vault`` is the 1Password vault's
    name or ID; ``fields`` maps each environment variable to the field it
    takes. Nothing is stored: the sandbox resolves the fields when the
    process starts.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    token: str
    vault: str
    fields: Dict[str, OnePasswordField]

    @field_validator("token")
    @classmethod
    def validate_token(cls, value):
        return validate_secret_name(value)

    @field_validator("vault")
    @classmethod
    def validate_vault(cls, value):
        return validate_onepassword_name(value, "The 1Password vault")

    @field_validator("fields", mode="before")
    @classmethod
    def validate_fields(cls, value):
        if not isinstance(value, dict):
            return value
        if not 1 <= len(value) <= MAX_SECRET_BINDINGS:
            raise ValueError(
                f"one_password takes 1 to {MAX_SECRET_BINDINGS} fields; "
                f"got {len(value)}"
            )
        for env in value:
            validate_secret_env_name(env, "a 1Password field")
        return value

    @model_validator(mode="after")
    def check_reference_sizes(self):
        for env, field in self.fields.items():
            size = len(
                onepassword_reference(self.vault, field).encode(
                    "utf-8", "surrogatepass"
                )
            )
            if size > MAX_ONEPASSWORD_REFERENCE_BYTES:
                raise ValueError(
                    f"{env}: the 1Password reference is {size} bytes; at most "
                    f"{MAX_ONEPASSWORD_REFERENCE_BYTES} are allowed"
                )
        return self


def onepassword_clashes(
    one_password: Optional[OnePasswordSource], **sources
) -> Optional[str]:
    """Describe a variable ``one_password`` shares with another source of the
    request (``secrets`` or ``env``), or return ``None``. Clashes with a vault
    are only known to the server."""
    if one_password is None:
        return None
    for name, variables in sources.items():
        for env in one_password.fields:
            if variables and env in variables:
                return (
                    f"{env} is set by {name} and by one_password; a 1Password "
                    "field's variable must come from it alone"
                )
    return None


# What a secret's value is; fixed when the secret is created.
#   secret    an opaque string: an environment variable, and typed into pages
#             on its allowed origins
#   totp      a TOTP seed (base32 or an otpauth://totp/ URI): delivered and
#             typed as the code that is current at the time
#   op_token  a 1Password service account token, used only to sign in for
#             one_password fields
SecretType = Literal["secret", "totp", "op_token"]

# A secret value, encrypted locally before upload.
SecretValue = Union[str, bytes]


MAX_ALLOWED_ORIGINS = 20
MAX_ALLOWED_ORIGIN_LENGTH = 512
# The server's form for allowed origins: scheme://host[:port], where the host
# may start with "*." to match any subdomain. ASCII only, as in JavaScript
# without the u flag: no Unicode case folding or digits.
_ALLOWED_ORIGIN_PATTERN = re.compile(
    r"([a-z]+)://(\*\.)?([^/:?#]+|\[[^\]]+\])(?::([0-9]{1,5}))?/?",
    re.IGNORECASE | re.ASCII,
)
_ORIGIN_HOST_LABEL = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)", re.ASCII)
_LOCAL_ORIGIN_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})


def validate_allowed_origin(entry) -> str:
    """Check an allowed origin as the server normalizes one, returning it
    unchanged: ``scheme://host[:port]`` with no path, https only (http for
    localhost, 127.0.0.1 and [::1]), and a ``*.`` wildcard only on a
    registrable domain."""
    if not isinstance(entry, str):
        raise ValueError(
            f"Allowed origin {entry!r} must be a string such as https://example.com"
        )
    if _utf16_length(entry) > MAX_ALLOWED_ORIGIN_LENGTH:
        raise ValueError(
            f"Allowed origin {entry[:64]!r} is longer than "
            f"{MAX_ALLOWED_ORIGIN_LENGTH} characters"
        )

    def reject(reason: str) -> ValueError:
        return ValueError(f"Allowed origin {entry!r} {reason}")

    match = _ALLOWED_ORIGIN_PATTERN.fullmatch(entry.strip())
    if not match:
        raise reject("must be scheme://host[:port] with no path")
    scheme, wildcard, host, port = match.groups()
    scheme = scheme.lower()
    host = host.lower()
    if scheme not in ("https", "http"):
        raise reject("must use https")
    if scheme == "http" and (wildcard or host not in _LOCAL_ORIGIN_HOSTS):
        raise reject("must use https unless it is localhost")
    if port and int(port) > 65535:
        raise reject("has an invalid port")
    if not host.startswith("["):
        labels = host.split(".")
        if not all(_ORIGIN_HOST_LABEL.fullmatch(label) for label in labels):
            raise reject("has an invalid host")
        # "*.com" would cover a whole public suffix.
        if wildcard and len(labels) < 2:
            raise reject("wildcard must name a registrable domain")
        # No top-level domain is numeric, so this is (part of) an IPv4 address.
        if wildcard and labels[-1].isdigit():
            raise reject("cannot use a wildcard with an IP address")
    elif wildcard:
        raise reject("cannot use a wildcard with an IP address")
    else:
        try:
            ipaddress.IPv6Address(host[1:-1])
        except ValueError:
            raise reject("has an invalid host") from None
    return entry


def validate_allowed_origins(origins) -> List[str]:
    """Check a list of 1 to 20 allowed origins (see validate_allowed_origin)."""
    if isinstance(origins, (str, bytes)) or not isinstance(origins, (list, tuple)):
        raise ValueError(
            'allowed_origins must be a list of origins such as ["https://example.com"]'
        )
    if not 1 <= len(origins) <= MAX_ALLOWED_ORIGINS:
        raise ValueError(
            f"allowed_origins takes 1 to {MAX_ALLOWED_ORIGINS} origins; "
            f"got {len(origins)}"
        )
    return [validate_allowed_origin(origin) for origin in origins]


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
    allowed_origins: Optional[List[str]] = Field(default=None, exclude=True)
    # Encrypted locally and uploaded as the first version; never sent as is.
    value: Optional[SecretValue] = Field(default=None, exclude=True, repr=False)

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
        if self.metadata is not None and self.metadata.browser is not None:
            if self.type == "op_token":
                raise ValueError(
                    "An op_token secret can't have allowed origins: it is never "
                    "typed into browser pages"
                )
            validate_allowed_origins(self.metadata.browser.allowed_origins)
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
    encryption_context: str = Field(alias="encryptionContext")
    latest_version: Optional[int] = Field(default=None, alias="latestVersion")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    @field_validator("type", "metadata", mode="before")
    @classmethod
    def default_when_null(cls, value, info):
        if value is not None:
            return value
        return "secret" if info.field_name == "type" else {}


class SecretVersion(SecretBaseModel):
    version: int
    kid: str
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")


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
