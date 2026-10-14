import time
from typing import Dict, Optional, Sequence, Union

from ..._request import coerce_request, dump_request
from ....exceptions import HyperbrowserError
from ....models.secret import (
    CreateSecretParams,
    Secret,
    SecretDeleteResult,
    SecretDetail,
    SecretListParams,
    SecretListResponse,
    SecretsPublicKey,
    SecretVersion,
    SecretValue,
    SecretVersionDeleteResult,
    UpdateSecretParams,
)
from ....sandbox_common import (
    ensure_response_ok,
    get_retry_delay_seconds,
    normalize_network_error,
    parse_json_response,
    request_context,
    should_retry_get,
)
from ....secrets_common import (
    SECRET_NAME_LOOKUP_LIMIT,
    SecretsSealer,
    browser_metadata,
    check_secret_version,
    is_not_found,
    looks_like_secret_id,
    secret_not_found_error,
    secret_payload_bytes,
    secret_value_not_stored_error,
    update_secret_body,
)
from ....types import CreateSecretParams as CreateSecretParamsDict
from ....types import SecretListParams as SecretListParamsDict
from ....types import UpdateSecretParams as UpdateSecretParamsDict


class SecretManager:
    """Manage encrypted secrets for sandbox processes and startup commands.

    Values are encrypted on this machine to the platform's public key and are
    never returned by the API. Methods that take ``secret`` accept a secret's
    ID or its exact name.
    """

    def __init__(self, client):
        self._client = client

    def get_public_key(self) -> SecretsPublicKey:
        return SecretsPublicKey(**self._request("GET", "/secrets/public-key"))

    def list(
        self,
        params: Optional[Union[SecretListParamsDict, SecretListParams]] = None,
    ) -> SecretListResponse:
        payload = self._request(
            "GET",
            "/secrets",
            params=dump_request(
                params if params is not None else {},
                SecretListParams,
            ),
        )
        return SecretListResponse(**payload)

    def create(
        self,
        params: Union[CreateSecretParamsDict, CreateSecretParams],
    ) -> Secret:
        """Create a secret, and store its first version when ``value`` is set.

        ``type`` is ``"secret"`` (the default), ``"totp"`` (a base32 seed or an
        ``otpauth://totp/`` URI) or ``"op_token"`` (a 1Password service
        account token, which starts with ``ops_``). ``allowed_origins`` makes
        a ``secret`` or ``totp`` fillable into browser pages on those origins.

        The value and the public key are checked before the secret is created,
        so a bad value or an unavailable key leaves nothing behind.
        """
        normalized = coerce_request(params, CreateSecretParams)
        payload = None
        sealer = None
        if normalized.value is not None:
            payload = secret_payload_bytes(
                normalized.type or "secret", normalized.value
            )
            sealer = SecretsSealer(self.get_public_key())
        secret = Secret(
            **self._request(
                "POST",
                "/secrets",
                data=normalized.model_dump(by_alias=True, exclude_none=True),
            )
        )
        if sealer is None or payload is None:
            return secret
        try:
            version = self._add_version(secret, payload, sealer)
        except Exception as error:
            raise secret_value_not_stored_error(secret.id, secret.name, error)
        return secret.model_copy(update={"latest_version": version.version})

    def get(self, secret: str) -> SecretDetail:
        detail, complete = self._resolve(secret)
        if complete:
            return detail
        return self._get_by_id(detail.id)

    def update(
        self,
        secret: str,
        params: Union[UpdateSecretParamsDict, UpdateSecretParams],
    ) -> Secret:
        """Update a secret's description or metadata.

        Metadata is merged by top-level member: each member sent replaces the
        stored one, ``None`` removes it, and members not sent are kept.
        """
        body = update_secret_body(params)
        resolved = self._resolve(secret)[0]
        payload = self._request("PATCH", f"/secrets/{resolved.id}", data=body)
        return Secret(**payload)

    def set_allowed_origins(
        self, secret: str, allowed_origins: Optional[Sequence[str]]
    ) -> Secret:
        """Replace the origins a secret may be filled on; ``None`` clears
        them, after which it can't be filled. Not for ``op_token`` secrets."""
        return self.update(secret, {"metadata": browser_metadata(allowed_origins)})

    def add_version(self, secret: str, value: SecretValue) -> SecretVersion:
        """Encrypt ``value`` locally and store it as the secret's next version.

        The value is checked against the secret's type first: a ``totp``
        secret takes a base32 seed or an ``otpauth://totp/`` URI.
        """
        secret_payload_bytes(None, value)
        resolved = self._resolve(secret)[0]
        payload = secret_payload_bytes(resolved.type, value)
        return self._add_version(
            resolved, payload, SecretsSealer(self.get_public_key())
        )

    def delete(self, secret: str) -> SecretDeleteResult:
        """Delete a secret and all its versions. Values already delivered to
        sandboxes are not revoked."""
        secret_id = self._resolve(secret)[0].id
        return SecretDeleteResult(**self._request("DELETE", f"/secrets/{secret_id}"))

    def delete_version(self, secret: str, version: int) -> SecretVersionDeleteResult:
        """Delete one version. The latest version can't be deleted."""
        check_secret_version(version)
        secret_id = self._resolve(secret)[0].id
        payload = self._request("DELETE", f"/secrets/{secret_id}/versions/{version}")
        return SecretVersionDeleteResult(**payload)

    def _add_version(
        self, secret: Secret, payload: bytes, sealer: SecretsSealer
    ) -> SecretVersion:
        # Always the context the API returned; it differs by secret type.
        envelope = sealer.seal(secret.encryption_context, payload)
        payload = self._request(
            "POST", f"/secrets/{secret.id}/versions", data={"envelope": envelope}
        )
        return SecretVersion(**payload)

    def _get_by_id(self, secret_id: str) -> SecretDetail:
        return SecretDetail(**self._request("GET", f"/secrets/{secret_id}"))

    def _resolve(self, key: str):
        """Find a secret by ID or exact name, reporting whether the result
        already includes its versions."""
        key = key.strip()
        if looks_like_secret_id(key):
            try:
                return self._get_by_id(key), True
            except HyperbrowserError as error:
                if not is_not_found(error):
                    raise
        listing = self.list({"search": key, "limit": SECRET_NAME_LOOKUP_LIMIT})
        for item in listing.secrets:
            if item.name == key:
                return SecretDetail(**item.model_dump()), False
        raise secret_not_found_error(key)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        data: Optional[Dict[str, object]] = None,
    ):
        failed_attempt = 1
        while True:
            try:
                response = self._client.transport.client.request(
                    method,
                    self._client._build_url(path),
                    params={
                        key: value
                        for key, value in (params or {}).items()
                        if value is not None
                    },
                    json=data,
                )
                ensure_response_ok(response, "control")
            except BaseException as cause:
                error = normalize_network_error(
                    cause,
                    "control",
                    "Unknown error occurred",
                    request_context(method, path),
                )
                if not should_retry_get(method, error, failed_attempt):
                    raise error
                time.sleep(get_retry_delay_seconds(failed_attempt))
                failed_attempt += 1
                continue

            return parse_json_response(response, "control")
