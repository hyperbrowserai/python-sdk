from typing import Any, Dict, Optional

from hyperbrowser.models import (
    FetchParams,
    GetBatchFetchJobParams,
    GetWebCrawlJobParams,
    StartBatchFetchJobParams,
    StartWebCrawlJobParams,
    WebSearchParams,
)

from ..schema_utils import inject_web_output_schemas
from .serialization_utils import (
    serialize_model_dump_or_default,
    serialize_model_dump_to_dict,
)


def build_web_fetch_payload(params: FetchParams) -> Dict[str, Any]:
    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize web fetch params",
    )
    inject_web_output_schemas(payload, params.outputs.formats if params.outputs else None)
    return payload


def build_web_search_payload(params: WebSearchParams) -> Dict[str, Any]:
    return serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize web search params",
    )


def build_batch_fetch_start_payload(params: StartBatchFetchJobParams) -> Dict[str, Any]:
    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize batch fetch start params",
    )
    inject_web_output_schemas(payload, params.outputs.formats if params.outputs else None)
    return payload


def build_web_crawl_start_payload(params: StartWebCrawlJobParams) -> Dict[str, Any]:
    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize web crawl start params",
    )
    inject_web_output_schemas(payload, params.outputs.formats if params.outputs else None)
    return payload


def build_batch_fetch_get_params(
    params: Optional[GetBatchFetchJobParams] = None,
) -> Dict[str, Any]:
    return serialize_model_dump_or_default(
        params,
        default_factory=GetBatchFetchJobParams,
        error_message="Failed to serialize batch fetch get params",
    )


def build_web_crawl_get_params(
    params: Optional[GetWebCrawlJobParams] = None,
) -> Dict[str, Any]:
    return serialize_model_dump_or_default(
        params,
        default_factory=GetWebCrawlJobParams,
        error_message="Failed to serialize web crawl get params",
    )
