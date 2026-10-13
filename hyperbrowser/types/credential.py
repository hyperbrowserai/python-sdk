"""Typed dictionary requests for filling stored credentials into pages."""

from typing import List, Optional

from typing_extensions import Required, TypedDict


class CredentialFillField(TypedDict):
    """Types the credential's ``field`` (a key of the stored value, such as
    ``"username"``) into the input matching the CSS ``selector``."""

    field: str
    selector: str


class CredentialFillFrame(TypedDict):
    """Selects an iframe by URL prefix."""

    url: str


class FillCredentialParams(TypedDict, total=False):
    """Fill 1-16 fields of a credential attached to the session.

    ``page_id`` is a CDP target ID, needed when several tabs could be the
    target; ``frame`` selects an iframe by URL prefix.
    """

    credential: Required[str]
    fields: Required[List[CredentialFillField]]
    page_id: Optional[str]
    frame: Optional[CredentialFillFrame]


__all__ = [
    "CredentialFillField",
    "CredentialFillFrame",
    "FillCredentialParams",
]
