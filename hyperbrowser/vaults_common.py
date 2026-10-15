"""Vault request rules shared by the sync and async clients."""

from typing import Any, Dict

from .client._request import coerce_request
from .exceptions import HyperbrowserError
from .models.vault import CreateVaultParams, StoredEntry, UpdateVaultParams


def _entry_body(entry: StoredEntry) -> Dict[str, Any]:
    # Only the request members: entries read from a vault also carry
    # secretId, which the API doesn't take.
    body: Dict[str, Any] = {"name": entry.name}
    if entry.version is not None:
        body["version"] = entry.version
    return body


def create_vault_body(params: Any) -> Dict[str, Any]:
    """Check a vault create request locally and return its JSON body."""
    request = coerce_request(params, CreateVaultParams)
    body: Dict[str, Any] = {"name": request.name}
    if request.description is not None:
        body["description"] = request.description
    if request.entries is not None:
        body["entries"] = {
            env: _entry_body(entry) for env, entry in request.entries.items()
        }
    return body


def update_vault_body(params: Any) -> Dict[str, Any]:
    """Check a vault update locally and return its JSON body.

    Members left out or ``None`` are not sent; an entry set to ``None`` is
    sent as ``null``, which removes that variable.
    """
    request = coerce_request(params, UpdateVaultParams)
    body: Dict[str, Any] = {}
    if request.description is not None:
        body["description"] = request.description
    if request.entries is not None:
        body["entries"] = {
            env: None if entry is None else _entry_body(entry)
            for env, entry in request.entries.items()
        }
    return body


def vault_not_found_error(key: str) -> HyperbrowserError:
    return HyperbrowserError(
        f'Vault "{key}" not found',
        status_code=404,
        code="VAULT_NOT_FOUND",
        retryable=False,
        service="control",
    )
