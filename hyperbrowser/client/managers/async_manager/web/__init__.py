from typing import Union

from hyperbrowser.client._request import dump_request, dump_request_with_fetch_schemas
from hyperbrowser.types import (
    FetchParams as FetchParamsDict,
    WebSearchParams as WebSearchParamsDict,
)

from .batch_fetch import BatchFetchManager
from .crawl import WebCrawlManager
from hyperbrowser.models import (
    FetchParams,
    FetchResponse,
    WebSearchParams,
    WebSearchResponse,
)


class WebManager:
    def __init__(self, client):
        self._client = client
        self.batch_fetch = BatchFetchManager(client)
        self.crawl = WebCrawlManager(client)

    async def fetch(
        self,
        params: Union[FetchParamsDict, FetchParams],
    ) -> FetchResponse:
        response = await self._client.transport.post(
            self._client._build_url("/web/fetch"),
            data=dump_request_with_fetch_schemas(params, FetchParams),
        )
        return FetchResponse(**response.data)

    async def search(
        self,
        params: Union[WebSearchParamsDict, WebSearchParams],
    ) -> WebSearchResponse:
        response = await self._client.transport.post(
            self._client._build_url("/web/search"),
            data=dump_request(params, WebSearchParams),
        )
        return WebSearchResponse(**response.data)
