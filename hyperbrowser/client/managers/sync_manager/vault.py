from typing import Optional, Tuple, Union

from ..._request import dump_request
from ....customer_key import CustomerKeys, check_customer_keys
from ....exceptions import HyperbrowserError
from ....models.vault import (
    CreateVaultParams,
    UpdateVaultParams,
    Vault,
    VaultDeleteResult,
    VaultListParams,
    VaultListResponse,
    VaultReference,
    VaultUnwrappedEntry,
    WrappedVault,
)
from ....secrets_common import (
    SECRET_NAME_LOOKUP_LIMIT,
    is_not_found,
    looks_like_secret_id,
)
from ....types import CreateVaultParams as CreateVaultParamsDict
from ....types import UpdateVaultParams as UpdateVaultParamsDict
from ....types import VaultListParams as VaultListParamsDict
from ....vaults_common import (
    create_vault_body,
    update_vault_body,
    vault_not_found_error,
)
from .secret import SecretManager


class VaultManager:
    """Manage vaults: named sets of environment variables whose values come
    from stored secrets.

    Pass a vault by name as ``vault`` when creating a sandbox or starting a
    process, or as ``{"vault": name}`` in a browser session's
    ``credentials``. Methods that take ``vault`` accept its ID or exact name.

    A vault with customer-protected entries is passed to sandboxes and
    processes as the reference ``unwrap()`` returns.
    """

    def __init__(self, client):
        self._client = client
        # Vault routes share the secrets routes' errors and retries.
        self._control = SecretManager(client)

    def list(
        self,
        params: Optional[Union[VaultListParamsDict, VaultListParams]] = None,
    ) -> VaultListResponse:
        payload = self._control._request(
            "GET",
            "/vaults",
            params=dump_request(params if params is not None else {}, VaultListParams),
        )
        return VaultListResponse(**payload)

    def create(
        self,
        params: Union[CreateVaultParamsDict, CreateVaultParams],
    ) -> Vault:
        """Create a vault.

        ``entries`` maps environment variable names to
        ``{"name": secret, "version": N}`` (version optional).
        """
        body = create_vault_body(params)
        return Vault(**self._control._request("POST", "/vaults", data=body))

    def get(self, vault: str) -> Vault:
        return (self._resolve(vault))[0]

    def update(
        self,
        vault: str,
        params: Union[UpdateVaultParamsDict, UpdateVaultParams],
    ) -> Vault:
        """Update a vault's description, entries, or both.

        Each entry given replaces that variable and an entry set to ``None``
        removes it; entries not given are kept.
        """
        body = update_vault_body(params)
        vault_id = (self._resolve(vault))[1]
        payload = self._control._request("PATCH", f"/vaults/{vault_id}", data=body)
        return Vault(**payload)

    def delete(self, vault: str) -> VaultDeleteResult:
        """Delete a vault. Its secrets are kept."""
        vault_id = (self._resolve(vault))[1]
        payload = self._control._request("DELETE", f"/vaults/{vault_id}")
        return VaultDeleteResult(**payload)

    def get_wrapped(self, vault: str) -> WrappedVault:
        """The wrapped envelopes of a vault's customer-protected entries, at
        the versions they resolve to now. Most callers want ``unwrap()``."""
        vault_id = (self._resolve(vault))[1]
        payload = self._control._request("GET", f"/vaults/{vault_id}/wrapped")
        return WrappedVault(**payload)

    def unwrap(self, vault: str, customer_key: CustomerKeys) -> VaultReference:
        """Unwrap a vault's customer-protected entries locally with your own
        key.

        Returns the reference a sandbox's or process's ``vault`` takes; its
        other entries are delivered as usual. If an entry moves to another
        secret or version before it is used, the API refuses the reference
        with ``SECRET_VAULT_CHANGED``; unwrap the vault again.
        ``customer_key`` may be a list; each entry uses the key whose ``kid``
        wrapped it.
        """
        check_customer_keys(customer_key)
        wrapped = self.get_wrapped(vault)
        unwrapped = {}
        for env, entry in wrapped.entries.items():
            inner = self._control._unwrap(
                entry, customer_key, f"Entry {env} of vault {wrapped.name}"
            )
            unwrapped[env] = VaultUnwrappedEntry(version=entry.version, unwrapped=inner)
        return VaultReference(name=wrapped.name, unwrapped=unwrapped)

    def _resolve(self, key: str) -> Tuple[Vault, str]:
        """Find a vault by ID or exact name."""
        key = key.strip()
        if looks_like_secret_id(key):
            try:
                found = Vault(**self._control._request("GET", f"/vaults/{key}"))
                return found, found.id
            except HyperbrowserError as error:
                if not is_not_found(error):
                    raise
        listing = self.list({"search": key, "limit": SECRET_NAME_LOOKUP_LIMIT})
        for item in listing.vaults:
            if item.name == key:
                return item, item.id
        raise vault_not_found_error(key)
