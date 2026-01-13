from .batch_fetch import BatchFetchManager
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

    def fetch(self, params: FetchParams) -> FetchResponse:
        if params.outputs and params.outputs.formats:
            for output in params.outputs.formats:
                if isinstance(output, FetchOutputJson) and output.schema_:
                    if hasattr(output.schema_, "model_json_schema"):
                        output.schema_ = jsonref.replace_refs(
                            output.schema_.model_json_schema(),
                            proxies=False,
                            lazy_load=False,
                        )

        response = self._client.transport.post(
            self._client._build_url("/web/fetch"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return FetchResponse(**response.data)

    def search(self, params: WebSearchParams) -> WebSearchResponse:
        response = self._client.transport.post(
            self._client._build_url("/web/search"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return WebSearchResponse(**response.data)
