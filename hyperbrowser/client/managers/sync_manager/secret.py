import time
from typing import Dict, List, Literal, Optional, Sequence, Union

from ..._request import coerce_request, dump_request
from ....customer_key import (
    CustomerKey,
    CustomerKeys,
    check_customer_key,
    check_customer_keys,
    check_unwrapped,
    customer_key_for,
    secret_envelope_digest,
    sync_result,
)
from ....exceptions import HyperbrowserError
from ....models.secret import (
    CreateSecretParams,
    ReplaceSecretVersionWrappingParams,
    Secret,
    SecretDeleteResult,
    SecretDetail,
    SecretListParams,
    SecretListResponse,
    SecretReference,
    SecretsPublicKey,
    SecretVersion,
    SecretValue,
    SecretVersionDeleteResult,
    UpdateSecretParams,
    WrappedSecretVersion,
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
    check_customer_protection,
    check_secret_version,
    check_secret_version_or_latest,
    create_secret_protection,
    invalid_request,
    is_not_found,
    looks_like_secret_id,
    secret_not_found_error,
    secret_payload_bytes,
    secret_value_not_stored_error,
    update_secret_body,
)
from ....types import CreateSecretParams as CreateSecretParamsDict
from ....types import (
    ReplaceSecretVersionWrappingParams as ReplaceSecretVersionWrappingParamsDict,
)
from ....types import SecretListParams as SecretListParamsDict
from ....types import UpdateSecretParams as UpdateSecretParamsDict


class SecretManager:
    """Manage encrypted secrets for sandbox processes and startup commands.

    Values are encrypted on this machine to the platform's public key and are
    never returned by the API. Methods that take ``secret`` accept a secret's
    ID or its exact name.

    A customer-protected secret's versions are also wrapped locally with your
    own key (``create_customer_key()``, or your own ``CustomerKey``), so the
    platform stores nothing it can open alone. Each use passes the reference
    ``unwrap()`` returns.
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

        ``protection="customer"`` wraps each version with your own key as
        well; passing ``customer_key`` implies it, and wraps the first version.

        The value and the public key are checked before the secret is created,
        so a bad value or an unavailable key leaves nothing behind.
        """
        normalized = coerce_request(params, CreateSecretParams)
        protection = create_secret_protection(normalized)
        payload = None
        sealer = None
        if normalized.value is not None:
            payload = secret_payload_bytes(
                normalized.type or "secret", normalized.value
            )
            sealer = SecretsSealer(self.get_public_key())
        body = normalized.model_dump(by_alias=True, exclude_none=True)
        if protection is not None:
            body["protection"] = protection
        secret = Secret(**self._request("POST", "/secrets", data=body))
        if sealer is None or payload is None:
            return secret
        try:
            version = self._add_version(
                secret, payload, sealer, normalized.customer_key
            )
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

    def add_version(
        self,
        secret: str,
        value: SecretValue,
        *,
        customer_key: Optional[CustomerKey] = None,
    ) -> SecretVersion:
        """Encrypt ``value`` locally and store it as the secret's next version.

        The value is checked against the secret's type first: a ``totp``
        secret takes a base32 seed or an ``otpauth://totp/`` URI. A
        customer-protected secret's value is also wrapped with
        ``customer_key``.
        """
        secret_payload_bytes(None, value)
        if customer_key is not None:
            check_customer_key(customer_key)
        resolved = self._resolve(secret)[0]
        check_customer_protection(resolved, customer_key)
        payload = secret_payload_bytes(resolved.type, value)
        return self._add_version(
            resolved, payload, SecretsSealer(self.get_public_key()), customer_key
        )

    def get_wrapped_version(
        self, secret: str, version: Union[int, Literal["latest"]] = "latest"
    ) -> WrappedSecretVersion:
        """A customer-protected version's wrapped envelope, for unwrapping with
        your own key. Most callers want ``unwrap()``, which also unwraps it."""
        check_secret_version_or_latest(version)
        secret_id = self._resolve(secret)[0].id
        return self._get_wrapped(secret_id, version)

    def unwrap(
        self,
        secret: str,
        customer_key: CustomerKeys,
        *,
        version: Union[int, Literal["latest"]] = "latest",
    ) -> SecretReference:
        """Unwrap a customer-protected version locally with your own key.

        Returns the reference each use passes: as a sandbox's or process's
        ``secrets`` entry, or as a 1Password ``token``. It is pinned to the
        version unwrapped. The unwrapped envelope is checked against the
        digest stored with the version, and only the platform can open it.
        ``customer_key`` may be a list, such as during a rotation; the key
        whose ``kid`` wrapped the version is used.
        """
        check_secret_version_or_latest(version)
        check_customer_keys(customer_key)
        resolved = self._resolve(secret)[0]
        wrapped = self._get_wrapped(resolved.id, version)
        inner = self._unwrap(
            wrapped,
            customer_key,
            f"Version {wrapped.version} of secret {resolved.name}",
        )
        return SecretReference(
            name=resolved.name, version=wrapped.version, unwrapped=inner
        )

    def rewrap(
        self,
        secret: str,
        *,
        from_key: CustomerKeys,
        to_key: CustomerKey,
        versions: Optional[Sequence[int]] = None,
    ) -> List[WrappedSecretVersion]:
        """Rewrap a customer-protected secret's versions with a new key, for
        rotating your own key.

        Each version is unwrapped with ``from_key`` and wrapped with
        ``to_key`` locally; the value never changes and the platform never
        sees it. Without ``versions``, every version not yet wrapped with
        ``to_key`` is rewrapped, so an interrupted rotation can be resumed.
        Returns the versions rewrapped.
        """
        check_customer_keys(from_key, "from_key")
        check_customer_key(to_key, "to_key")
        if versions is not None:
            if isinstance(versions, (str, bytes)):
                raise invalid_request("versions must be a list of version numbers")
            for version in versions:
                check_secret_version(version)
        detail = self.get(secret)
        if detail.protection != "customer":
            raise invalid_request(
                f"Secret {detail.name} is not customer-protected; it has no wrapping"
            )
        wanted = (
            list(versions)
            if versions is not None
            else [
                item.version for item in detail.versions if item.outer_kid != to_key.kid
            ]
        )
        rewrapped = []
        for version in wanted:
            wrapped = self._get_wrapped(detail.id, version)
            inner = self._unwrap(
                wrapped, from_key, f"Version {version} of secret {detail.name}"
            )
            envelope = sync_result(
                to_key.wrap(inner, detail.encryption_context), "wrap"
            )
            rewrapped.append(
                self._replace_wrapping(
                    detail.id, version, envelope, wrapped.inner_digest
                )
            )
        return rewrapped

    def replace_version_wrapping(
        self,
        secret: str,
        version: int,
        params: Union[
            ReplaceSecretVersionWrappingParamsDict, ReplaceSecretVersionWrappingParams
        ],
    ) -> WrappedSecretVersion:
        """Replace a customer-protected version's outer envelope with one you
        wrapped yourself. ``inner_digest`` must match the version's: only the
        wrapping changes, never the value. ``rewrap()`` does this for you."""
        check_secret_version(version)
        request = coerce_request(params, ReplaceSecretVersionWrappingParams)
        secret_id = self._resolve(secret)[0].id
        return self._replace_wrapping(
            secret_id, version, request.envelope, request.inner_digest
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
        self,
        secret: Secret,
        payload: bytes,
        sealer: SecretsSealer,
        customer_key: Optional[CustomerKey] = None,
    ) -> SecretVersion:
        # Always the context the API returned; it differs by secret type.
        envelope = sealer.seal(secret.encryption_context, payload)
        data: Dict[str, object] = {"envelope": envelope}
        if customer_key is not None:
            data = {
                "envelope": sync_result(
                    customer_key.wrap(envelope, secret.encryption_context), "wrap"
                ),
                "innerDigest": secret_envelope_digest(envelope),
                "innerKid": sealer.kid,
            }
        response = self._request("POST", f"/secrets/{secret.id}/versions", data=data)
        return SecretVersion(**response)

    def _get_wrapped(
        self, secret_id: str, version: Union[int, str]
    ) -> WrappedSecretVersion:
        return WrappedSecretVersion(
            **self._request("GET", f"/secrets/{secret_id}/versions/{version}/wrapped")
        )

    def _replace_wrapping(
        self, secret_id: str, version: int, envelope: str, inner_digest: str
    ) -> WrappedSecretVersion:
        payload = self._request(
            "PUT",
            f"/secrets/{secret_id}/versions/{version}/wrapping",
            data={"envelope": envelope, "innerDigest": inner_digest},
        )
        return WrappedSecretVersion(**payload)

    @staticmethod
    def _unwrap(wrapped: WrappedSecretVersion, keys: CustomerKeys, label: str) -> str:
        key = customer_key_for(keys, wrapped.outer_kid, label)
        inner = sync_result(key.unwrap(wrapped.envelope), "unwrap")
        return check_unwrapped(inner, wrapped.inner_digest, label)

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
