from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class SecretBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SecretReference(SecretBaseModel):
    """Selects a stored secret for an environment variable.

    An omitted version (or ``"latest"``) means the latest version.
    """

    name: str
    version: Optional[Union[int, Literal["latest"]]] = None


SecretReferenceInput = Union[str, SecretReference]


def normalize_secret_references(value):
    """Accept a plain secret name as shorthand for ``{"name": name}``."""
    if not isinstance(value, dict):
        return value
    return {
        env: {"name": reference} if isinstance(reference, str) else reference
        for env, reference in value.items()
    }


class CreateSecretParams(SecretBaseModel):
    name: str
    description: Optional[str] = None
    # Encrypted locally and uploaded as the first version; never sent as is.
    value: Optional[Union[str, bytes]] = Field(default=None, exclude=True)


class UpdateSecretParams(SecretBaseModel):
    description: str


class SecretListParams(SecretBaseModel):
    page: Optional[int] = None
    limit: Optional[int] = None
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
