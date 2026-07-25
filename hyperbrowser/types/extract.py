from typing import List, Optional, Union

from typing_extensions import Required, TypedDict

from ._json import JSONSchemaInput
from .session import CreateSessionParams


class _StartExtractParams(TypedDict, total=False):
    """Fields shared by Extract API and tool requests."""

    urls: Required[List[str]]
    system_prompt: Optional[str]
    prompt: Optional[str]
    wait_for: Optional[int]
    session_options: Optional[CreateSessionParams]
    max_links: Optional[int]


class StartExtractJobParams(_StartExtractParams, total=False):
    """Parameters for starting a website extraction job."""

    schema: Optional[JSONSchemaInput]


class WebsiteExtractToolParams(_StartExtractParams, total=False):
    """Parameters accepted by the website extraction tool wrapper."""

    schema: Optional[Union[JSONSchemaInput, str]]


__all__ = ["StartExtractJobParams", "WebsiteExtractToolParams"]
