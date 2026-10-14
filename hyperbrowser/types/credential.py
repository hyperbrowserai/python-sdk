"""Typed dictionary requests for filling secrets into browser pages."""

from typing import List, Optional

from typing_extensions import Required, TypedDict


class CredentialFillField(TypedDict, total=False):
    """Types a value into the input matching the CSS ``selector``. With a
    ``vault`` fill, ``field`` names the vault entry to type."""

    selector: Required[str]
    field: Optional[str]


class FillCredentialParams(TypedDict, total=False):
    """Fill 1-16 inputs from a secret (``credential``) or a vault's entries
    (``vault``) attached to the session.

    ``page_id`` (a CDP target ID) or ``page_url`` (a URL prefix) picks the tab
    when several could be the target; ``frame_url`` (a URL prefix) picks an
    iframe.
    """

    credential: Optional[str]
    vault: Optional[str]
    fields: Required[List[CredentialFillField]]
    page_id: Optional[str]
    page_url: Optional[str]
    frame_url: Optional[str]


__all__ = [
    "CredentialFillField",
    "FillCredentialParams",
]
