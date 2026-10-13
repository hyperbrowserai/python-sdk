"""Request and response models for filling stored credentials into pages."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# What a fill did with each requested field. New outcomes may be added, so
# results keep any string the server sends.
#   filled         the input now holds exactly the stored value
#   not_found      no input matched the selector
#   ambiguous      several visible inputs matched the selector
#   not_editable   the input is disabled, read-only, hidden or not a text input
#   not_accepted   the page didn't keep the value (for example maxlength)
#   not_populated  the stored credential has no such field
CredentialFillOutcome = Literal[
    "filled",
    "not_found",
    "ambiguous",
    "not_editable",
    "not_accepted",
    "not_populated",
]


class CredentialFillField(BaseModel):
    """Types the credential's ``field`` (a key of the stored value, such as
    ``"username"``) into the input matching the CSS ``selector``."""

    model_config = ConfigDict(populate_by_name=True)

    field: str
    selector: str


class CredentialFillFrame(BaseModel):
    """Selects an iframe by URL prefix."""

    model_config = ConfigDict(populate_by_name=True)

    url: str


class FillCredentialParams(BaseModel):
    """Fill a credential attached to the session into the page's inputs.

    ``credential`` is the credential's name or ID. ``page_id`` is a CDP target
    ID; it is needed when several tabs could be the target.
    """

    model_config = ConfigDict(populate_by_name=True)

    credential: str
    fields: List[CredentialFillField]
    page_id: Optional[str] = Field(default=None, serialization_alias="pageId")
    frame: Optional[CredentialFillFrame] = None


class CredentialFieldResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    field: str
    # One of CredentialFillOutcome; kept as str so new outcomes still parse.
    outcome: str


class CredentialFillResult(BaseModel):
    """The outcome of a fill, per field. Values are never returned."""

    model_config = ConfigDict(populate_by_name=True)

    # The credential version that was filled.
    version: int
    page_id: Optional[str] = Field(default=None, alias="pageId")
    origin: Optional[str] = None
    fields: List[CredentialFieldResult] = Field(default_factory=list)
