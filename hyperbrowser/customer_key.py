"""Customer keys for customer-protected secrets.

A customer-protected secret's versions are sealed to the platform's key as
usual, then wrapped again with the customer's own key, so nothing the
platform stores can be opened without it. Each use passes the envelope
unwrapped with that key.

``create_customer_key`` builds a key from local key material. To keep the
private key elsewhere, such as in a KMS or HSM, implement ``CustomerKey``.
"""

import base64
import hashlib
import inspect
import json
import os
import re
from typing import (
    Any,
    Awaitable,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, x448, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.keywrap import (
    InvalidUnwrap,
    aes_key_unwrap,
    aes_key_wrap,
)
from typing_extensions import Protocol, runtime_checkable

from .exceptions import HyperbrowserError

# How a customer key wraps an envelope (JWE key management). RSA keys use
# RSA-OAEP-256; EC and X25519/X448 keys use ECDH-ES+A256KW unless ECDH-ES is
# chosen. Content is always encrypted with A256GCM.
CustomerKeyAlgorithm = Literal["RSA-OAEP-256", "ECDH-ES", "ECDH-ES+A256KW"]

_ALGORITHMS = ("RSA-OAEP-256", "ECDH-ES", "ECDH-ES+A256KW")
_ENC = "A256GCM"
_IV_BYTES = 12
_TAG_BYTES = 16
_CEK_BYTES = 32
# The server's limit on an inner envelope.
MAX_INNER_ENVELOPE_LENGTH = 64 * 1024
MIN_RSA_KEY_BITS = 2048
MAX_CUSTOMER_KEY_ID_LENGTH = 256
_KID_PATTERN = re.compile(r"^[\x20-\x7e]+$")
_B64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]*$")
_CURVES = {
    "P-256": ec.SECP256R1,
    "P-384": ec.SECP384R1,
    "P-521": ec.SECP521R1,
}
_OKP = {
    "X25519": (x25519.X25519PrivateKey, x25519.X25519PublicKey),
    "X448": (x448.X448PrivateKey, x448.X448PublicKey),
}
_OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)

_PublicKey = Union[
    rsa.RSAPublicKey,
    ec.EllipticCurvePublicKey,
    x25519.X25519PublicKey,
    x448.X448PublicKey,
]
_PrivateKey = Union[
    rsa.RSAPrivateKey,
    ec.EllipticCurvePrivateKey,
    x25519.X25519PrivateKey,
    x448.X448PrivateKey,
]
# A key as create_customer_key takes it: a cryptography key object, a PEM or
# DER private or public key, or a JWK. A public key can only wrap.
CustomerKeyInput = Union[_PrivateKey, _PublicKey, str, bytes, Mapping[str, Any]]


@runtime_checkable
class CustomerKey(Protocol):
    """The customer's own key for customer-protected secrets.

    ``kid`` is written as the ``kid`` of every envelope the key wraps: 1-256
    printable ASCII characters. ``wrap`` returns a compact JWE (RSA-OAEP-256,
    ECDH-ES or ECDH-ES+A256KW with A256GCM) whose protected header holds
    exactly ``alg``, ``enc``, ``kid`` and ``ctx`` (plus ``epk``, and
    optionally ``apu`` and ``apv``, with ECDH-ES), with ``ctx`` set to
    ``encryption_context``. ``unwrap`` returns the inner envelope.

    With the async client, either method may return an awaitable.
    """

    @property
    def kid(self) -> str: ...

    def wrap(
        self, inner_envelope: str, encryption_context: str
    ) -> Union[str, Awaitable[str]]: ...

    def unwrap(self, wrapped_envelope: str) -> Union[str, Awaitable[str]]: ...


def _key_error(message: str, code: str = "invalid_customer_key") -> HyperbrowserError:
    return HyperbrowserError(message, code=code, retryable=False)


def _unwrap_failed(message: str) -> HyperbrowserError:
    return _key_error(message, "customer_key_unwrap_failed")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode_segment(segment: str, what: str) -> bytes:
    if _B64URL_PATTERN.fullmatch(segment):
        decoded = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
        if _b64url(decoded) == segment:
            return decoded
    raise _unwrap_failed(f"Wrapped envelope {what} is not canonical base64url")


def _jwk_bytes(jwk: Mapping[str, Any], member: str) -> bytes:
    value = jwk.get(member)
    if not isinstance(value, str) or not _B64URL_PATTERN.fullmatch(value):
        raise _key_error(f"The customer key JWK's {member!r} is not base64url")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _jwk_int(jwk: Mapping[str, Any], member: str) -> int:
    return int.from_bytes(_jwk_bytes(jwk, member), "big")


def _int_bytes(value: int, length: Optional[int] = None) -> bytes:
    size = length if length is not None else max(1, (value.bit_length() + 7) // 8)
    return value.to_bytes(size, "big")


def _uint32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def _length_prefixed(data: bytes) -> bytes:
    return _uint32(len(data)) + data


def _concat_kdf(shared: bytes, algorithm_id: str, apu: bytes, apv: bytes) -> bytes:
    """RFC 7518 section 4.6.2 Concat KDF with SHA-256, for one 256-bit key."""
    return hashlib.sha256(
        _uint32(1)
        + shared
        + _length_prefixed(algorithm_id.encode("ascii"))
        + _length_prefixed(apu)
        + _length_prefixed(apv)
        + _uint32(_CEK_BYTES * 8)
    ).digest()


def _curve_name(curve: ec.EllipticCurve) -> Optional[str]:
    for name, curve_type in _CURVES.items():
        if isinstance(curve, curve_type):
            return name
    return None


def _public_members(public_key: _PublicKey) -> Dict[str, str]:
    """The members of a public JWK that RFC 7638 thumbprints (and ``epk``
    headers) hold, in thumbprint order."""
    if isinstance(public_key, rsa.RSAPublicKey):
        numbers = public_key.public_numbers()
        return {
            "e": _b64url(_int_bytes(numbers.e)),
            "kty": "RSA",
            "n": _b64url(_int_bytes(numbers.n)),
        }
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        numbers = public_key.public_numbers()
        size = (public_key.curve.key_size + 7) // 8
        return {
            "crv": _curve_name(public_key.curve) or "",
            "kty": "EC",
            "x": _b64url(_int_bytes(numbers.x, size)),
            "y": _b64url(_int_bytes(numbers.y, size)),
        }
    raw = public_key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    crv = "X25519" if isinstance(public_key, x25519.X25519PublicKey) else "X448"
    return {"crv": crv, "kty": "OKP", "x": _b64url(raw)}


def _thumbprint(public_key: _PublicKey) -> str:
    """The RFC 7638 SHA-256 thumbprint of a public key."""
    members = json.dumps(_public_members(public_key), separators=(",", ":"))
    return _b64url(hashlib.sha256(members.encode("ascii")).digest())


def _jwk_public_key(jwk: Mapping[str, Any]) -> _PublicKey:
    kty = jwk.get("kty")
    if kty == "RSA":
        return rsa.RSAPublicNumbers(_jwk_int(jwk, "e"), _jwk_int(jwk, "n")).public_key()
    if kty == "EC":
        curve = _CURVES.get(jwk.get("crv"))  # type: ignore[arg-type]
        if curve is None:
            raise _key_error("EC customer keys must be on P-256, P-384 or P-521")
        return ec.EllipticCurvePublicNumbers(
            _jwk_int(jwk, "x"), _jwk_int(jwk, "y"), curve()
        ).public_key()
    if kty == "OKP":
        okp = _OKP.get(jwk.get("crv"))  # type: ignore[arg-type]
        if okp is None:
            raise _key_error("OKP customer keys must be X25519 or X448")
        return okp[1].from_public_bytes(_jwk_bytes(jwk, "x"))
    raise _key_error(
        "A customer key must be RSA, EC (P-256, P-384, P-521), X25519 or X448"
    )


def _jwk_private_key(jwk: Mapping[str, Any], public_key: _PublicKey) -> _PrivateKey:
    kty = jwk.get("kty")
    private_key: _PrivateKey
    if kty == "RSA":
        assert isinstance(public_key, rsa.RSAPublicKey)
        public_numbers = public_key.public_numbers()
        d = _jwk_int(jwk, "d")
        if "p" in jwk and "q" in jwk:
            p, q = _jwk_int(jwk, "p"), _jwk_int(jwk, "q")
        else:
            p, q = rsa.rsa_recover_prime_factors(public_numbers.n, public_numbers.e, d)
        private_key = rsa.RSAPrivateNumbers(
            p=p,
            q=q,
            d=d,
            dmp1=rsa.rsa_crt_dmp1(d, p),
            dmq1=rsa.rsa_crt_dmq1(d, q),
            iqmp=rsa.rsa_crt_iqmp(p, q),
            public_numbers=public_numbers,
        ).private_key()
    elif kty == "EC":
        assert isinstance(public_key, ec.EllipticCurvePublicKey)
        private_key = ec.derive_private_key(_jwk_int(jwk, "d"), public_key.curve)
    else:
        private_key = _OKP[jwk["crv"]][0].from_private_bytes(_jwk_bytes(jwk, "d"))
    if _public_members(private_key.public_key()) != _public_members(public_key):
        raise _key_error(
            "The customer key JWK's private and public members don't match"
        )
    return private_key


def _load_pem_or_der(
    data: bytes,
) -> Tuple[Any, Optional[Any]]:
    pem = data.lstrip().startswith(b"-----BEGIN")
    load_private = (
        serialization.load_pem_private_key
        if pem
        else serialization.load_der_private_key
    )
    load_public = (
        serialization.load_pem_public_key if pem else serialization.load_der_public_key
    )
    try:
        private_key = load_private(data, password=None)
        return private_key.public_key(), private_key
    except TypeError:
        raise _key_error(
            "The customer key is encrypted; pass the decrypted key object instead"
        ) from None
    except ValueError:
        pass
    try:
        return load_public(data), None
    except ValueError:
        raise _key_error("The customer key is not a PEM or DER key") from None


def _load_keys(key: Any) -> Tuple[Any, Optional[Any], Optional[str]]:
    if isinstance(key, Mapping):
        jwk_kid = key.get("kid") if isinstance(key.get("kid"), str) else None
        try:
            public_key = _jwk_public_key(key)
            private_key = _jwk_private_key(key, public_key) if "d" in key else None
        except HyperbrowserError:
            raise
        except (ValueError, TypeError, KeyError) as error:
            raise HyperbrowserError(
                "The customer key JWK could not be read",
                code="invalid_customer_key",
                cause=error,
            ) from None
        return public_key, private_key, jwk_kid
    if isinstance(key, str):
        key = key.encode("utf-8")
    if isinstance(key, (bytes, bytearray)):
        public_key, private_key = _load_pem_or_der(bytes(key))
        return public_key, private_key, None
    if isinstance(
        key,
        (
            rsa.RSAPrivateKey,
            ec.EllipticCurvePrivateKey,
            x25519.X25519PrivateKey,
            x448.X448PrivateKey,
        ),
    ):
        return key.public_key(), key, None
    if isinstance(
        key,
        (
            rsa.RSAPublicKey,
            ec.EllipticCurvePublicKey,
            x25519.X25519PublicKey,
            x448.X448PublicKey,
        ),
    ):
        return key, None, None
    raise _key_error(
        "A customer key must be RSA, EC (P-256, P-384, P-521), X25519 or X448: "
        "a key object, a PEM or DER key, or a JWK"
    )


def check_customer_key_id(kid: Any) -> str:
    """Raise unless ``kid`` is a key ID the API stores: 1-256 printable ASCII
    characters."""
    if (
        not isinstance(kid, str)
        or len(kid) > MAX_CUSTOMER_KEY_ID_LENGTH
        or not _KID_PATTERN.fullmatch(kid)
    ):
        raise _key_error(
            f"A customer key's kid must be 1-{MAX_CUSTOMER_KEY_ID_LENGTH} "
            "printable ASCII characters"
        )
    return kid


class LocalCustomerKey:
    """A customer key held in this process. Build one with
    ``create_customer_key``."""

    def __init__(
        self,
        public_key: Any,
        private_key: Optional[Any],
        *,
        kid: Optional[str] = None,
        algorithm: Optional[CustomerKeyAlgorithm] = None,
    ):
        if isinstance(public_key, rsa.RSAPublicKey):
            if public_key.key_size < MIN_RSA_KEY_BITS:
                raise _key_error(
                    f"RSA customer keys must be at least {MIN_RSA_KEY_BITS} bits"
                )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            if _curve_name(public_key.curve) is None:
                raise _key_error("EC customer keys must be on P-256, P-384 or P-521")
        elif not isinstance(public_key, (x25519.X25519PublicKey, x448.X448PublicKey)):
            raise _key_error(
                "A customer key must be RSA, EC (P-256, P-384, P-521), X25519 or X448"
            )
        is_rsa = isinstance(public_key, rsa.RSAPublicKey)
        if algorithm is None:
            algorithm = "RSA-OAEP-256" if is_rsa else "ECDH-ES+A256KW"
        if algorithm not in _ALGORITHMS:
            raise _key_error(f"Unsupported customer key algorithm {algorithm!r}")
        if (algorithm == "RSA-OAEP-256") != is_rsa:
            raise _key_error(
                "RSA customer keys wrap with RSA-OAEP-256"
                if is_rsa
                else "EC and X25519/X448 customer keys wrap with ECDH-ES or "
                "ECDH-ES+A256KW"
            )
        self._public_key = public_key
        self._private_key = private_key
        self._algorithm: str = algorithm
        self._kid = check_customer_key_id(
            kid if kid is not None else _thumbprint(public_key)
        )

    @property
    def kid(self) -> str:
        return self._kid

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def can_unwrap(self) -> bool:
        """Whether this key holds its private key, so can unwrap."""
        return self._private_key is not None

    def __repr__(self) -> str:
        return f"LocalCustomerKey(kid={self._kid!r}, algorithm={self._algorithm!r})"

    def _ephemeral(self) -> Any:
        if isinstance(self._public_key, ec.EllipticCurvePublicKey):
            return ec.generate_private_key(self._public_key.curve)
        if isinstance(self._public_key, x25519.X25519PublicKey):
            return x25519.X25519PrivateKey.generate()
        return x448.X448PrivateKey.generate()

    @staticmethod
    def _exchange(private_key: Any, public_key: Any) -> bytes:
        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            return private_key.exchange(ec.ECDH(), public_key)
        return private_key.exchange(public_key)

    def wrap(self, inner_envelope: str, encryption_context: str) -> str:
        """Wrap an inner envelope as a compact JWE bound to
        ``encryption_context``."""
        if not isinstance(inner_envelope, str) or not inner_envelope:
            raise _key_error(
                "The envelope to wrap must be a non-empty string", "invalid_request"
            )
        if len(inner_envelope) > MAX_INNER_ENVELOPE_LENGTH:
            raise _key_error(
                "The envelope to wrap is larger than 64 KiB", "invalid_request"
            )
        if not isinstance(encryption_context, str) or not encryption_context:
            raise _key_error(
                "An encryption context is required to wrap an envelope",
                "invalid_request",
            )
        header: Dict[str, Any] = {
            "alg": self._algorithm,
            "enc": _ENC,
            "kid": self._kid,
            "ctx": encryption_context,
        }
        encrypted_key = b""
        if isinstance(self._public_key, rsa.RSAPublicKey):
            cek = os.urandom(_CEK_BYTES)
            encrypted_key = self._public_key.encrypt(cek, _OAEP)
        else:
            ephemeral = self._ephemeral()
            header["epk"] = _public_members(ephemeral.public_key())
            shared = self._exchange(ephemeral, self._public_key)
            algorithm_id = _ENC if self._algorithm == "ECDH-ES" else self._algorithm
            derived = _concat_kdf(shared, algorithm_id, b"", b"")
            if self._algorithm == "ECDH-ES":
                cek = derived
            else:
                cek = os.urandom(_CEK_BYTES)
                encrypted_key = aes_key_wrap(derived, cek)
        protected = _b64url(
            json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        )
        iv = os.urandom(_IV_BYTES)
        sealed = AESGCM(cek).encrypt(
            iv, inner_envelope.encode("utf-8"), protected.encode("ascii")
        )
        return ".".join(
            [
                protected,
                _b64url(encrypted_key),
                _b64url(iv),
                _b64url(sealed[:-_TAG_BYTES]),
                _b64url(sealed[-_TAG_BYTES:]),
            ]
        )

    def unwrap(self, wrapped_envelope: str) -> str:
        """Decrypt an envelope this key wrapped and return the inner
        envelope."""
        if self._private_key is None:
            raise _key_error(
                f"Customer key {self._kid} has no private key, so it can wrap but "
                "not unwrap",
                "customer_key_private_key_required",
            )
        if not isinstance(wrapped_envelope, str):
            raise _unwrap_failed("The wrapped envelope must be a string")
        segments = wrapped_envelope.split(".")
        if len(segments) != 5:
            raise _unwrap_failed("The wrapped envelope must have five segments")
        header_segment, key_segment, iv_segment, ciphertext_segment, tag_segment = (
            segments
        )
        try:
            header = json.loads(
                _decode_segment(header_segment, "header").decode("utf-8")
            )
        except (ValueError, UnicodeDecodeError):
            raise _unwrap_failed("The wrapped envelope header is not JSON") from None
        if not isinstance(header, dict):
            raise _unwrap_failed("The wrapped envelope header is not a JSON object")
        if header.get("kid") != self._kid:
            raise _key_error(
                f"The envelope was wrapped with key {json.dumps(header.get('kid'))}, "
                f"not {json.dumps(self._kid)}",
                "customer_key_mismatch",
            )
        if header.get("enc") != _ENC:
            raise _unwrap_failed(
                f"Unsupported wrapped envelope encryption {header.get('enc')}"
            )
        alg = header.get("alg")
        encrypted_key = _decode_segment(key_segment, "encrypted key")
        iv = _decode_segment(iv_segment, "IV")
        ciphertext = _decode_segment(ciphertext_segment, "ciphertext")
        tag = _decode_segment(tag_segment, "tag")
        if len(iv) != _IV_BYTES or len(tag) != _TAG_BYTES:
            raise _unwrap_failed("The wrapped envelope IV or tag has the wrong length")

        is_rsa = isinstance(self._private_key, rsa.RSAPrivateKey)
        try:
            if alg == "RSA-OAEP-256" and is_rsa:
                cek = self._private_key.decrypt(encrypted_key, _OAEP)
            elif alg in ("ECDH-ES", "ECDH-ES+A256KW") and not is_rsa:
                epk = header.get("epk")
                if not isinstance(epk, dict):
                    raise _unwrap_failed("The wrapped envelope has no epk")
                shared = self._exchange(self._private_key, _jwk_public_key(epk))

                def optional(name: str) -> bytes:
                    value = header.get(name)
                    return b"" if value is None else _decode_segment(str(value), name)

                derived = _concat_kdf(
                    shared,
                    _ENC if alg == "ECDH-ES" else alg,
                    optional("apu"),
                    optional("apv"),
                )
                cek = (
                    derived
                    if alg == "ECDH-ES"
                    else aes_key_unwrap(derived, encrypted_key)
                )
            else:
                raise _unwrap_failed(
                    f"Customer key {self._kid} can't unwrap an envelope wrapped with {alg}"
                )
        except HyperbrowserError as error:
            if error.code == "invalid_customer_key":
                raise _unwrap_failed(f"The wrapped envelope's epk is invalid: {error}")
            raise
        except (ValueError, TypeError, InvalidUnwrap) as error:
            raise HyperbrowserError(
                "The wrapped envelope's key could not be decrypted",
                code="customer_key_unwrap_failed",
                cause=error,
            ) from None
        if len(cek) != _CEK_BYTES:
            raise _unwrap_failed(
                "The wrapped envelope's content key has the wrong length"
            )
        try:
            plaintext = AESGCM(cek).decrypt(
                iv, ciphertext + tag, header_segment.encode("ascii")
            )
        except InvalidTag as error:
            raise HyperbrowserError(
                "The wrapped envelope could not be decrypted",
                code="customer_key_unwrap_failed",
                cause=error,
            ) from None
        try:
            return plaintext.decode("utf-8")
        except UnicodeDecodeError:
            raise _unwrap_failed("The wrapped envelope does not hold text") from None


def create_customer_key(
    key: CustomerKeyInput,
    *,
    kid: Optional[str] = None,
    algorithm: Optional[CustomerKeyAlgorithm] = None,
) -> LocalCustomerKey:
    """A customer key from local key material: RSA (at least 2048 bits), EC
    (P-256, P-384 or P-521), X25519 or X448, as a key object, a PEM or DER
    key, or a JWK. With only the public key it can wrap (upload versions)
    but not unwrap (use them).

    ``kid`` defaults to the JWK's ``kid``, or else the RFC 7638 thumbprint of
    the public key, so the same key always gets the same ID. ``algorithm`` is
    for EC and X25519/X448 keys, and defaults to ``ECDH-ES+A256KW``.
    """
    public_key, private_key, jwk_kid = _load_keys(key)
    return LocalCustomerKey(
        public_key,
        private_key,
        kid=kid if kid is not None else jwk_kid,
        algorithm=algorithm,
    )


def secret_envelope_digest(envelope: str) -> str:
    """Identify an inner envelope as the API does: the unpadded base64url
    SHA-256 of its compact form."""
    return _b64url(hashlib.sha256(envelope.encode("utf-8")).digest())


def check_customer_key(key: Any, what: str = "customer_key") -> CustomerKey:
    """Raise unless ``key`` looks like a ``CustomerKey``."""
    if (
        key is None
        or isinstance(key, (str, bytes, Mapping))
        or not callable(getattr(key, "wrap", None))
        or not callable(getattr(key, "unwrap", None))
    ):
        raise HyperbrowserError(
            f"{what} must be a customer key, such as one from create_customer_key()",
            code="invalid_request",
        )
    check_customer_key_id(getattr(key, "kid", None))
    return key


CustomerKeys = Union[CustomerKey, Sequence[CustomerKey]]


def check_customer_keys(keys: Any, what: str = "customer_key") -> List[CustomerKey]:
    """Raise unless ``keys`` is a customer key or a non-empty list of them."""
    if not isinstance(keys, (list, tuple)):
        return [check_customer_key(keys, what)]
    if not keys:
        raise HyperbrowserError(
            f"Pass at least one customer key as {what}", code="invalid_request"
        )
    return [
        check_customer_key(key, f"{what}[{index}]") for index, key in enumerate(keys)
    ]


def customer_key_for(keys: Any, kid: str, label: str) -> CustomerKey:
    """The key among ``keys`` that wrapped an envelope with this ``kid``."""
    for candidate in check_customer_keys(keys):
        if candidate.kid == kid:
            return candidate
    raise HyperbrowserError(
        f"{label} was wrapped with customer key {json.dumps(kid)}, which none of "
        "the keys given has",
        code="customer_key_mismatch",
    )


def check_unwrapped(inner: Any, inner_digest: str, label: str) -> str:
    """Raise unless ``inner`` is the inner envelope a version holds."""
    if not isinstance(inner, str) or secret_envelope_digest(inner) != inner_digest:
        raise HyperbrowserError(
            f"{label} unwrapped to an envelope that doesn't match its innerDigest; "
            "it may have been uploaded with the wrong digest",
            code="customer_key_unwrap_failed",
        )
    return inner


def _check_result(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise HyperbrowserError(
            f"The customer key's {what}() must return the envelope as a string",
            code="invalid_request",
        )
    return value


def sync_result(value: Any, what: str) -> str:
    """A customer key's result in the sync client, which can't await."""
    if inspect.isawaitable(value):
        close = getattr(value, "close", None)
        if callable(close):
            close()
        raise HyperbrowserError(
            f"The customer key's {what}() returned an awaitable; use the async "
            "client for keys whose methods are async",
            code="invalid_request",
        )
    return _check_result(value, what)


async def async_result(value: Any, what: str) -> str:
    """A customer key's result in the async client, awaited when needed."""
    if inspect.isawaitable(value):
        value = await value
    return _check_result(value, what)


__all__ = [
    "CustomerKey",
    "CustomerKeyAlgorithm",
    "CustomerKeyInput",
    "CustomerKeys",
    "LocalCustomerKey",
    "create_customer_key",
    "secret_envelope_digest",
]
