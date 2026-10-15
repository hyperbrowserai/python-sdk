"""Typed dictionary requests for filling secrets into browser pages."""

from typing import List, Optional

from typing_extensions import Required, TypedDict

from .secret import OnePasswordField


class CredentialFillField(TypedDict, total=False):
    """Types a value into the input matching the CSS ``selector``. With a
    ``vault`` fill, ``field`` names the vault entry to type; with a
    ``one_password`` fill, ``ref`` names the 1Password field."""

    selector: Required[str]
    field: Optional[str]
    ref: Optional[OnePasswordField]


class OnePasswordFillSource(TypedDict):
    """1Password fields read with the ``op_token`` secret named ``token``
    (attached to the session) from ``vault``, typed only on
    ``allowed_origins`` (1-20 origins such as ``https://example.com``)."""

    token: str
    vault: str
    allowed_origins: List[str]


class FillCredentialParams(TypedDict, total=False):
    """Fill 1-16 inputs from a secret (``credential``), a vault's entries
    (``vault``) or 1Password fields (``one_password``) attached to the
    session.

    ``page_id`` (a CDP target ID) or ``page_url`` (a URL prefix) picks the tab
    when several could be the target; ``frame_url`` (a URL prefix) picks an
    iframe.
    """

    credential: Optional[str]
    vault: Optional[str]
    one_password: Optional[OnePasswordFillSource]
    fields: Required[List[CredentialFillField]]
    page_id: Optional[str]
    page_url: Optional[str]
    frame_url: Optional[str]


__all__ = [
    "CredentialFillField",
    "FillCredentialParams",
    "OnePasswordFillSource",
]
