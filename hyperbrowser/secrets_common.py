"""Client-side secret encryption and helpers shared by the sync and async clients.

Secret values are encrypted on this machine to the platform's public key as a
compact JWE bound to the secret's encryption context. The API only ever
receives the envelope; only the sandbox host can decrypt it.
"""

import base64
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, Union

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .exceptions import HyperbrowserError
from .models.secret import SecretsPublicKey, validate_secret_version

# The largest secret value the platform accepts.
MAX_SECRET_VALUE_BYTES = 32 * 1024
# The same key policy the server and the sandbox hosts enforce.
MIN_SECRETS_KEY_BITS = 3072
SECRETS_KEY_EXPONENT = 65537
# The server's ID check: a hyphenated UUID, without braces or a urn: prefix.
SECRET_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
# Name lookups read one page of search results, which covers every secret
# while teams are limited to 100.
SECRET_NAME_LOOKUP_LIMIT = 100


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _int_bytes(value: int) -> bytes:
    return value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")


def secret_value_bytes(value: Union[str, bytes, bytearray]) -> bytes:
    """Return a secret value's bytes after applying the platform's rules.

    Values are used byte-for-byte, including trailing newlines.
    """
    if isinstance(value, str):
        data = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray)):
        data = bytes(value)
    else:
        raise TypeError(
            f"secret value must be str or bytes, got {type(value).__name__}"
        )
    if not data:
        raise HyperbrowserError("Secret value is empty", code="invalid_secret_value")
    if len(data) > MAX_SECRET_VALUE_BYTES:
        raise HyperbrowserError(
            f"Secret value is {len(data)} bytes; the limit is {MAX_SECRET_VALUE_BYTES}",
            code="invalid_secret_value",
        )
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise HyperbrowserError(
            "Secret value must be valid UTF-8", code="invalid_secret_value"
        ) from None
    if b"\x00" in data:
        raise HyperbrowserError(
            "Secret value must not contain NUL bytes", code="invalid_secret_value"
        )
    return data


def secrets_key_id(public_key: rsa.RSAPublicKey) -> str:
    """The RFC 7638 JWK SHA-256 thumbprint of an RSA key."""
    numbers = public_key.public_numbers()
    thumbprint_input = '{"e":"%s","kty":"RSA","n":"%s"}' % (
        _b64url(_int_bytes(numbers.e)),
        _b64url(_int_bytes(numbers.n)),
    )
    return _b64url(hashlib.sha256(thumbprint_input.encode("ascii")).digest())


def _invalid_key(message: str) -> HyperbrowserError:
    return HyperbrowserError(message, code="invalid_secrets_public_key")


class SecretsSealer:
    """Encrypts secret values with a verified secrets public key."""

    def __init__(self, key: Union[SecretsPublicKey, Dict[str, Any]]):
        if not isinstance(key, SecretsPublicKey):
            key = SecretsPublicKey.model_validate(key)
        if key.alg != "RSA-OAEP-256" or key.enc != "A256GCM" or key.jwk.kty != "RSA":
            raise _invalid_key(f"Unsupported secrets key ({key.alg}/{key.enc})")
        try:
            n = int.from_bytes(_b64url_decode(key.jwk.n), "big")
            e_bytes = _b64url_decode(key.jwk.e)
        except ValueError:
            raise _invalid_key("Secrets public key is not valid base64url") from None
        if n == 0 or not e_bytes or len(e_bytes) > 4:
            raise _invalid_key("Secrets public key has an invalid modulus or exponent")
        e = int.from_bytes(e_bytes, "big")
        if n.bit_length() < MIN_SECRETS_KEY_BITS or e != SECRETS_KEY_EXPONENT:
            raise _invalid_key(
                f"Secrets public key must be at least {MIN_SECRETS_KEY_BITS}-bit RSA "
                f"with exponent {SECRETS_KEY_EXPONENT}"
            )
        public_key = rsa.RSAPublicNumbers(e, n).public_key()
        # The key ID is derived from the key itself, so a mismatch means a
        # corrupted response or a misconfigured server. It does not prove where
        # the key came from: that rests on TLS to the API.
        if secrets_key_id(public_key) != key.kid:
            raise _invalid_key("Secrets public key does not match its key ID")
        self.kid = key.kid
        self._public_key = public_key

    def seal(self, encryption_context: str, value: Union[str, bytes, bytearray]) -> str:
        """Encrypt a value as a compact JWE (RSA-OAEP-256 + A256GCM) bound to a
        secret's encryption context."""
        data = secret_value_bytes(value)
        header = json.dumps(
            {
                "alg": "RSA-OAEP-256",
                "enc": "A256GCM",
                "kid": self.kid,
                "ctx": encryption_context,
            },
            separators=(",", ":"),
        )
        protected = _b64url(header.encode("utf-8"))
        cek = os.urandom(32)
        iv = os.urandom(12)
        encrypted_key = self._public_key.encrypt(
            cek,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        sealed = AESGCM(cek).encrypt(iv, data, protected.encode("ascii"))
        ciphertext, tag = sealed[:-16], sealed[-16:]
        return ".".join(
            [
                protected,
                _b64url(encrypted_key),
                _b64url(iv),
                _b64url(ciphertext),
                _b64url(tag),
            ]
        )


def looks_like_secret_id(key: str) -> bool:
    """Whether a key is shaped like a secret ID. Names may be too, so a
    UUID-shaped key that isn't an ID is looked up as a name."""
    return SECRET_ID_PATTERN.match(key) is not None


def check_secret_version(version: int) -> int:
    """Check a version number before it is used in a request path."""
    try:
        return validate_secret_version(version)
    except (TypeError, ValueError) as error:
        raise HyperbrowserError(str(error), code="invalid_secret_version") from None


def secret_not_found_error(key: str) -> HyperbrowserError:
    return HyperbrowserError(
        f'Secret "{key}" not found',
        status_code=404,
        code="SECRET_NOT_FOUND",
        retryable=False,
        service="control",
    )


def is_not_found(error: HyperbrowserError) -> bool:
    return error.status_code == 404


def secret_value_not_stored_error(
    secret_id: str, name: str, cause: BaseException
) -> HyperbrowserError:
    return HyperbrowserError(
        f'Secret "{name}" ({secret_id}) was created, but storing its value failed: '
        f"{cause}. Store the value with secrets.add_version(); creating it again "
        "fails because the name is taken",
        code="secret_value_not_stored",
        retryable=False,
        service="control",
        details={"secretId": secret_id, "name": name},
        cause=cause,
        original_error=cause if isinstance(cause, Exception) else None,
    )


def request_may_have_arrived(error: BaseException) -> bool:
    """Whether a failed request may still have reached the API: it timed out,
    or its response couldn't be read. API errors and failures to connect are
    excluded."""
    if isinstance(error, HyperbrowserError):
        if isinstance(error.cause, json.JSONDecodeError):
            return True
        if error.status_code is not None:
            # An error status is the API's answer; a success status means the
            # response body couldn't be read.
            return error.status_code < 400
        cause = error.cause if error.cause is not None else error.original_error
        if cause is None or cause is error:
            return False
        return request_may_have_arrived(cause)
    return not isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout))


def secret_process_outcome_unknown_error(
    sandbox_id: str, cause: BaseException
) -> HyperbrowserError:
    return HyperbrowserError(
        "The process start may have reached the API, but no result came back; "
        f"the command may be running with its secrets. Check the processes of "
        f"sandbox {sandbox_id} before retrying",
        code="secret_process_outcome_unknown",
        retryable=False,
        service="control",
        details={"sandboxId": sandbox_id},
        cause=cause,
        original_error=cause if isinstance(cause, Exception) else None,
    )


def secret_process_start_error(
    sandbox_id: str, error: HyperbrowserError
) -> HyperbrowserError:
    """Report a failed process start with secrets.

    A start that may have reached the API, or that the API reports as
    unconfirmed, may be running with the secrets, so it must not look
    retryable.
    """
    if request_may_have_arrived(error):
        return secret_process_outcome_unknown_error(sandbox_id, error)
    if error.code == "SECRET_PROCESS_OUTCOME_UNKNOWN":
        # The server's body, including its code, stays in the details.
        details = dict(error.details) if isinstance(error.details, dict) else {}
        details["sandboxId"] = sandbox_id
        return HyperbrowserError(
            error.args[0],
            status_code=error.status_code,
            response=error.response,
            code="secret_process_outcome_unknown",
            request_id=error.request_id,
            retryable=False,
            service="control",
            details=details,
            cause=error,
            original_error=error,
        )
    return error


def sandbox_create_outcome_unknown_error(cause: BaseException) -> HyperbrowserError:
    """A create with startup secrets whose result is unknown: a sandbox may
    be running its startup command with the secrets."""
    # A response that fails validation describes every field; one line is enough.
    detail = (str(cause).splitlines() or [type(cause).__name__])[0]
    return HyperbrowserError(
        f"Could not confirm the create result: {detail}; a sandbox may have "
        "been created with the secrets, so list sandboxes before retrying",
        code="secret_process_outcome_unknown",
        retryable=False,
        service="control",
        cause=cause,
        original_error=cause if isinstance(cause, Exception) else None,
    )


def secret_process_id(process: Any) -> str:
    """A started process's ID; the receiver may send it as ``processId``."""
    if not isinstance(process, dict):
        return ""
    process_id = process.get("id") or process.get("processId")
    return process_id.strip() if isinstance(process_id, str) else ""


def secret_process_failed_error(
    sandbox_id: str, process_id: str, step: str, cause: BaseException
) -> HyperbrowserError:
    return HyperbrowserError(
        f"Process {process_id} started with secrets, but {step} failed: {cause}. "
        "It may still be running; check or kill it with "
        "sandbox.get_process() rather than running the command again",
        code="secret_process_failed",
        retryable=False,
        service="runtime",
        details={"processId": process_id, "sandboxId": sandbox_id},
        cause=cause,
        original_error=cause if isinstance(cause, Exception) else None,
    )


def missing_process_id_error(sandbox_id: str) -> HyperbrowserError:
    return HyperbrowserError(
        "The API accepted the process start but returned no process ID; the "
        f"command may be running, so check the processes of sandbox {sandbox_id} "
        "before retrying",
        code="secret_process_outcome_unknown",
        retryable=False,
        service="control",
        details={"sandboxId": sandbox_id},
    )


def secret_wait_chunk_ms(runtime_timeout_seconds: Optional[float]) -> int:
    """Keep each runtime wait request well under the client's request timeout."""
    timeout = runtime_timeout_seconds or 30
    return max(1, min(20_000, int(timeout * 1000 / 2)))


@dataclass(frozen=True)
class SecretProcessWaitContext:
    sandbox_id: str
    runtime_timeout_seconds: Optional[float]


class SecretProcessWait:
    """One local wait deadline across bounded receiver requests."""

    def __init__(
        self,
        context: SecretProcessWaitContext,
        timeout_ms: Optional[int],
        timeout_sec: Optional[int],
        timeout_error: Type[Exception] = TimeoutError,
    ):
        timeout = None
        if timeout_sec is not None and timeout_sec > 0:
            timeout = timeout_sec
        elif timeout_ms is not None and timeout_ms > 0:
            timeout = timeout_ms / 1000
        self.deadline = time.monotonic() + timeout if timeout is not None else None
        self.chunk_ms = secret_wait_chunk_ms(context.runtime_timeout_seconds)
        self.runtime_timeout_seconds = context.runtime_timeout_seconds
        self.timeout_error = timeout_error

    def remaining(self) -> Optional[float]:
        if self.deadline is None:
            return None
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise self.timeout_error("Timed out waiting for command output")
        return remaining

    def request_budget(self):
        remaining = self.remaining()
        if remaining is None:
            return self.chunk_ms, None, None
        request_timeout = remaining
        if (
            self.runtime_timeout_seconds is not None
            and self.runtime_timeout_seconds > 0
        ):
            request_timeout = min(request_timeout, self.runtime_timeout_seconds)
        # Zero selects the receiver's default 30-second wait. Keep a positive
        # millisecond even when the local budget is below its wire precision.
        return (
            min(self.chunk_ms, max(1, int(remaining * 1000))),
            request_timeout,
            remaining,
        )

    def retry_delay(self, request_started_at: float) -> float:
        # A receiver normally blocks for the chunk before replying 408. Pace
        # immediate replies too, including sub-millisecond request budgets.
        delay = max(0.0, 0.01 - (time.monotonic() - request_started_at))
        remaining = self.remaining()
        return min(delay, remaining) if remaining is not None else delay
