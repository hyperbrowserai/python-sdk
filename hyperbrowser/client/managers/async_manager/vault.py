from typing import Optional, Tuple, Union

from ..._request import dump_request
from ....exceptions import HyperbrowserError
from ....models.vault import (
    CreateVaultParams,
    UpdateVaultParams,
    Vault,
    VaultDeleteResult,
    VaultListParams,
    VaultListResponse,
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
    from stored secrets or from a 1Password vault.

    Pass a vault by name as ``vault`` when creating a sandbox or starting a
    process, or as ``{"vault": name}`` in a browser session's
    ``credentials``. Methods that take ``vault`` accept its ID or exact name.
    """

    def __init__(self, client):
        self._client = client
        # Vault routes share the secrets routes' errors and retries.
        self._control = SecretManager(client)

    async def list(
        self,
        params: Optional[Union[VaultListParamsDict, VaultListParams]] = None,
    ) -> VaultListResponse:
        payload = await self._control._request(
            "GET",
            "/vaults",
            params=dump_request(params if params is not None else {}, VaultListParams),
        )
        return VaultListResponse(**payload)

    async def create(
        self,
        params: Union[CreateVaultParamsDict, CreateVaultParams],
    ) -> Vault:
        """Create a vault.

        ``source`` defaults to ``{"type": "stored"}``, whose entries are
        ``{"name": secret, "version": N}`` (version optional). A 1Password
        vault, ``{"type": "1password", "token_secret": op_token_secret,
        "vault": name_or_id}``, takes ``{"item", "section", "field"}`` entries.
        The source type can't change later.
        """
        body = create_vault_body(params)
        return Vault(**await self._control._request("POST", "/vaults", data=body))

    async def get(self, vault: str) -> Vault:
        return (await self._resolve(vault))[0]

    async def update(
        self,
        vault: str,
        params: Union[UpdateVaultParamsDict, UpdateVaultParams],
    ) -> Vault:
        """Update a vault's description, entries or 1Password settings.

        Each entry given replaces that variable and an entry set to ``None``
        removes it; entries not given are kept. ``source`` takes
        ``token_secret`` and/or ``vault``, for 1Password vaults only.
        """
        body = update_vault_body(params)
        vault_id = (await self._resolve(vault))[1]
        payload = await self._control._request(
            "PATCH", f"/vaults/{vault_id}", data=body
        )
        return Vault(**payload)

    async def delete(self, vault: str) -> VaultDeleteResult:
        """Delete a vault. Its secrets are kept."""
        vault_id = (await self._resolve(vault))[1]
        payload = await self._control._request("DELETE", f"/vaults/{vault_id}")
        return VaultDeleteResult(**payload)

    async def _resolve(self, key: str) -> Tuple[Vault, str]:
        """Find a vault by ID or exact name."""
        key = key.strip()
        if looks_like_secret_id(key):
            try:
                found = Vault(**await self._control._request("GET", f"/vaults/{key}"))
                return found, found.id
            except HyperbrowserError as error:
                if not is_not_found(error):
                    raise
        listing = await self.list({"search": key, "limit": SECRET_NAME_LOOKUP_LIMIT})
        for item in listing.vaults:
            if item.name == key:
                return item, item.id
        raise vault_not_found_error(key)
