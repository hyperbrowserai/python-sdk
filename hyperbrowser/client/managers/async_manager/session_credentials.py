from typing import Union
from urllib.parse import quote

from hyperbrowser.credentials_common import (
    CREDENTIAL_FILL_REQUEST_TIMEOUT_SECONDS,
    fill_credential_payload,
)
from hyperbrowser.models.credential import CredentialFillResult, FillCredentialParams
from hyperbrowser.types.credential import (
    FillCredentialParams as FillCredentialParamsDict,
)


class SessionCredentialsManager:
    """Fill secrets attached to a session into its pages.

    Attach secrets, vaults or op_token secrets (for 1Password fields) with
    ``sessions.create({"credentials": [...]})``.
    """

    def __init__(self, client):
        self._client = client

    async def fill(
        self,
        session_id: str,
        params: Union[FillCredentialParamsDict, FillCredentialParams],
    ) -> CredentialFillResult:
        """Type a secret, a vault's entries, or 1Password fields into the
        inputs matching each selector.

        Pass ``credential`` (a secret's name or ID) with
        ``[{"selector": ...}]``, ``vault`` with
        ``[{"field": ENTRY, "selector": ...}]``, or ``one_password``
        (``{"token", "vault", "allowed_origins"}``) with
        ``[{"ref": {"item", "section", "field"}, "selector": ...}]``. A
        TOTP secret types the code that is current at fill time. Fill never
        submits: click the login button or press Enter afterwards. It is safe to retry. Values are
        never returned; each input reports an outcome such as ``filled`` or
        ``not_found``. When several tabs could be the target, the API fails
        with ``CREDENTIAL_PAGE_AMBIGUOUS`` and lists them in
        ``error.details["details"]["pages"]``; pass one's ``pageId`` as
        ``page_id``, or a URL prefix as ``page_url``.
        """
        body = fill_credential_payload(params)
        response = await self._client.transport.post(
            self._client._build_url(
                f"/session/{quote(session_id, safe='')}/credentials/fill"
            ),
            data=body,
            timeout=max(self._client.timeout, CREDENTIAL_FILL_REQUEST_TIMEOUT_SECONDS),
        )
        return CredentialFillResult(**response.data)
