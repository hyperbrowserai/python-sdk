from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
import pydantic

from hyperbrowser.models.session import CreateSessionParams

ExtractJobStatus = Literal["pending", "running", "completed", "failed"]


class StartExtractJobParams(BaseModel):
    """
    Parameters for creating a new extract job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    urls: List[str]
    system_prompt: Optional[str] = Field(
        default=None, serialization_alias="systemPrompt"
    )
    prompt: Optional[str] = Field(default=None, serialization_alias="prompt")
    schema_: Optional[Any] = pydantic.Field(
        None, alias="schema", serialization_alias="schema"
    )
    wait_for: Optional[int] = Field(default=None, serialization_alias="waitFor")
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
    )
    max_links: Optional[int] = Field(default=None, serialization_alias="maxLinks")


class StartExtractJobResponse(BaseModel):
    """
    Response from creating a extract job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class ExtractJobStatusResponse(BaseModel):
    """
    Response from getting the status of a extract job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: ExtractJobStatus


class ExtractJobResponse(BaseModel):
    """
    Response from a extract job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: ExtractJobStatus
    error: Optional[str] = None
    data: Optional[dict] = None
