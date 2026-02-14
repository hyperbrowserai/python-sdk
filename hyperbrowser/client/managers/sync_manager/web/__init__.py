from .batch_fetch import BatchFetchManager
from .crawl import WebCrawlManager
from hyperbrowser.models import (
    FetchParams,
    FetchResponse,
    WebSearchParams,
    WebSearchResponse,
)
from ...response_utils import parse_response_model
from ...web_payload_utils import build_web_fetch_payload, build_web_search_payload


class WebManager:
    def __init__(self, client):
        self._client = client
        self.batch_fetch = BatchFetchManager(client)
        self.crawl = WebCrawlManager(client)

    def fetch(self, params: FetchParams) -> FetchResponse:
        payload = build_web_fetch_payload(params)

        response = self._client.transport.post(
            self._client._build_url("/web/fetch"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=FetchResponse,
            operation_name="web fetch",
        )

    def search(self, params: WebSearchParams) -> WebSearchResponse:
        payload = build_web_search_payload(params)
        response = self._client.transport.post(
            self._client._build_url("/web/search"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=WebSearchResponse,
            operation_name="web search",
        )
