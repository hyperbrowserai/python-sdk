"""Request and response models for filling secrets into browser pages."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# What a fill did with each requested input. New outcomes may be added, so
# results keep any string the server sends.
#   filled         the input now holds the value
#   not_found      no input matched the selector
#   ambiguous      several visible inputs matched the selector
#   not_editable   the input is disabled, read-only, hidden or not a text input
#   not_accepted   the page didn't keep the value (for example maxlength)
CredentialFillOutcome = Literal[
    "filled",
    "not_found",
    "ambiguous",
    "not_editable",
    "not_accepted",
]


class CredentialFillField(BaseModel):
    """Types a value into the input matching the CSS ``selector``.

    With a ``vault`` fill, ``field`` names the vault entry (its environment
    variable name, such as ``"PASSWORD"``) whose secret is typed; without
    one it is left out.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    selector: str
    field: Optional[str] = None


class FillCredentialParams(BaseModel):
    """Fill a secret, or a vault's entries, attached to the session at
    creation into a page's inputs.

    Pass exactly one of ``credential`` (a secret's name or ID) and ``vault``
    (a vault's name). ``page_id`` (a CDP target ID) or ``page_url`` (a URL
    prefix) picks the tab when several could be the target; ``frame_url``
    (a URL prefix) picks an iframe.
    """

    # Unknown members fail rather than fill a page the caller didn't mean.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    credential: Optional[str] = None
    vault: Optional[str] = None
    fields: List[CredentialFillField]
    page_id: Optional[str] = Field(default=None, serialization_alias="pageId")
    page_url: Optional[str] = Field(default=None, serialization_alias="pageUrl")
    # Sent as {"frame": {"url": ...}}.
    frame_url: Optional[str] = Field(default=None, exclude=True)


class CredentialFieldResult(BaseModel):
    """What a fill did with one input. Values are never returned."""

    model_config = ConfigDict(populate_by_name=True)

    selector: str
    # One of CredentialFillOutcome; kept as str so new outcomes still parse.
    outcome: str
    secret_id: Optional[str] = Field(default=None, alias="secretId")
    version: Optional[int] = None
    # The vault entry, for vault fills.
    field: Optional[str] = None
    # When the typed TOTP code stops being valid, for TOTP secrets.
    expires_at: Optional[datetime] = Field(default=None, alias="expiresAt")


class CredentialFillResult(BaseModel):
    """The outcome of a fill, per input. Values are never returned."""

    model_config = ConfigDict(populate_by_name=True)

    # The secret version filled; set for single-secret fills only.
    version: Optional[int] = None
    page_id: Optional[str] = Field(default=None, alias="pageId")
    origin: Optional[str] = None
    fields: List[CredentialFieldResult] = Field(default_factory=list)
