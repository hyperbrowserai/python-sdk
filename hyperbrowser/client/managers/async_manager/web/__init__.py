from .batch_fetch import BatchFetchManager
from .crawl import WebCrawlManager
from hyperbrowser.models import (
    FetchParams,
    FetchResponse,
    WebSearchParams,
    WebSearchResponse,
)
from ....schema_utils import inject_web_output_schemas


class WebManager:
    def __init__(self, client):
        self._client = client
        self.batch_fetch = BatchFetchManager(client)
        self.crawl = WebCrawlManager(client)

    async def fetch(self, params: FetchParams) -> FetchResponse:
        payload = params.model_dump(exclude_none=True, by_alias=True)
        inject_web_output_schemas(
            payload, params.outputs.formats if params.outputs else None
        )

        response = await self._client.transport.post(
            self._client._build_url("/web/fetch"),
            data=payload,
        )
        return FetchResponse(**response.data)

    async def search(self, params: WebSearchParams) -> WebSearchResponse:
        response = await self._client.transport.post(
            self._client._build_url("/web/search"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return WebSearchResponse(**response.data)
