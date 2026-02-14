from .batch_fetch import BatchFetchManager
from .crawl import WebCrawlManager
from hyperbrowser.models import (
    FetchParams,
    FetchResponse,
    WebSearchParams,
    WebSearchResponse,
)
from ...web_operation_metadata import WEB_REQUEST_OPERATION_METADATA
from ...web_payload_utils import build_web_fetch_payload, build_web_search_payload
from ...web_request_utils import start_web_job
from ...web_route_constants import WEB_FETCH_ROUTE_PATH, WEB_SEARCH_ROUTE_PATH


class WebManager:
    _OPERATION_METADATA = WEB_REQUEST_OPERATION_METADATA
    _FETCH_ROUTE_PATH = WEB_FETCH_ROUTE_PATH
    _SEARCH_ROUTE_PATH = WEB_SEARCH_ROUTE_PATH

    def __init__(self, client):
        self._client = client
        self.batch_fetch = BatchFetchManager(client)
        self.crawl = WebCrawlManager(client)

    def fetch(self, params: FetchParams) -> FetchResponse:
        payload = build_web_fetch_payload(params)
        return start_web_job(
            client=self._client,
            route_prefix=self._FETCH_ROUTE_PATH,
            payload=payload,
            model=FetchResponse,
            operation_name=self._OPERATION_METADATA.fetch_operation_name,
        )

    def search(self, params: WebSearchParams) -> WebSearchResponse:
        payload = build_web_search_payload(params)
        return start_web_job(
            client=self._client,
            route_prefix=self._SEARCH_ROUTE_PATH,
            payload=payload,
            model=WebSearchResponse,
            operation_name=self._OPERATION_METADATA.search_operation_name,
        )
