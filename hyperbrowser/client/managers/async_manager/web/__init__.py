from .batch_fetch import BatchFetchManager
from .crawl import WebCrawlManager
from hyperbrowser.models import (
    FetchParams,
    FetchResponse,
    WebSearchParams,
    WebSearchResponse,
)
from ....schema_utils import inject_web_output_schemas
from ...serialization_utils import serialize_model_dump_to_dict
from ...response_utils import parse_response_model


class WebManager:
    def __init__(self, client):
        self._client = client
        self.batch_fetch = BatchFetchManager(client)
        self.crawl = WebCrawlManager(client)

    async def fetch(self, params: FetchParams) -> FetchResponse:
        payload = serialize_model_dump_to_dict(
            params,
            error_message="Failed to serialize web fetch params",
        )
        inject_web_output_schemas(
            payload, params.outputs.formats if params.outputs else None
        )

        response = await self._client.transport.post(
            self._client._build_url("/web/fetch"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=FetchResponse,
            operation_name="web fetch",
        )

    async def search(self, params: WebSearchParams) -> WebSearchResponse:
        payload = serialize_model_dump_to_dict(
            params,
            error_message="Failed to serialize web search params",
        )
        response = await self._client.transport.post(
            self._client._build_url("/web/search"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=WebSearchResponse,
            operation_name="web search",
        )
