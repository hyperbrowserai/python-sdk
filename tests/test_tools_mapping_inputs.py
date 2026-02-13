from types import MappingProxyType

from hyperbrowser.models.scrape import StartScrapeJobParams
from hyperbrowser.tools import WebsiteScrapeTool


class _Response:
    def __init__(self, data):
        self.data = data


class _ScrapeManager:
    def __init__(self):
        self.last_params = None

    def start_and_wait(self, params: StartScrapeJobParams):
        self.last_params = params
        return _Response(type("Data", (), {"markdown": "ok"})())


class _Client:
    def __init__(self):
        self.scrape = _ScrapeManager()


def test_tool_wrappers_accept_mapping_inputs():
    client = _Client()
    params = MappingProxyType({"url": "https://example.com"})

    output = WebsiteScrapeTool.runnable(client, params)

    assert output == "ok"
    assert isinstance(client.scrape.last_params, StartScrapeJobParams)
