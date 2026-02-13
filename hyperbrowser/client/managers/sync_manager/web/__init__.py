from .batch_fetch import BatchFetchManager
from .crawl import WebCrawlManager
from hyperbrowser.models import (
    FetchParams,
    FetchResponse,
    FetchOutputJson,
    WebSearchParams,
    WebSearchResponse,
)
import jsonref


class WebManager:
    def __init__(self, client):
        self._client = client
        self.batch_fetch = BatchFetchManager(client)
        self.crawl = WebCrawlManager(client)

    def fetch(self, params: FetchParams) -> FetchResponse:
        payload = params.model_dump(exclude_none=True, by_alias=True)
        if params.outputs and params.outputs.formats:
            for index, output in enumerate(params.outputs.formats):
                if isinstance(output, FetchOutputJson) and output.schema_:
                    if hasattr(output.schema_, "model_json_schema"):
                        payload["outputs"]["formats"][index]["schema"] = jsonref.replace_refs(
                            output.schema_.model_json_schema(),
                            proxies=False,
                            lazy_load=False,
                        )

        response = self._client.transport.post(
            self._client._build_url("/web/fetch"),
            data=payload,
        )
        return FetchResponse(**response.data)

    def search(self, params: WebSearchParams) -> WebSearchResponse:
        response = self._client.transport.post(
            self._client._build_url("/web/search"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return WebSearchResponse(**response.data)
