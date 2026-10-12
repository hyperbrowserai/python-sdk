import re
from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The server's rules for secret names, the environment variables secrets are
# delivered to, and version numbers.
SECRET_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")
SECRET_ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_SECRET_VERSION = 2**31 - 1
MAX_SECRET_BINDINGS = 32


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


class CreateSecretParams(SecretBaseModel):
    model_config = ConfigDict(populate_by_name=True, hide_input_in_errors=True)

    name: str
    description: Optional[str] = None
    # Encrypted locally and uploaded as the first version; never sent as is.
    value: Optional[Union[str, bytes]] = Field(default=None, exclude=True, repr=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return validate_secret_name(value)


class UpdateSecretParams(SecretBaseModel):
    description: str


class SecretListParams(SecretBaseModel):
    page: Optional[int] = Field(default=None, ge=1)
    limit: Optional[int] = Field(default=None, ge=1, le=100)
    search: Optional[str] = None


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
    encryption_context: str = Field(alias="encryptionContext")
    latest_version: Optional[int] = Field(default=None, alias="latestVersion")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


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


class SandboxResolvedSecret(SecretBaseModel):
    """The secret version a process environment variable received."""

    env: str
    name: str
    secret_id: str = Field(alias="secretId")
    version: int
