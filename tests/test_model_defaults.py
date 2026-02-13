from hyperbrowser.models.agents.hyper_agent import HyperAgentOutput
from hyperbrowser.models.crawl import StartCrawlJobParams
from hyperbrowser.models.session import CreateSessionParams
from hyperbrowser.models.web.common import FetchBrowserOptions


def test_create_session_params_locales_are_not_shared():
    first = CreateSessionParams()
    second = CreateSessionParams()

    first.locales.append("fr")

    assert second.locales == ["en"]


def test_start_crawl_patterns_are_not_shared():
    first = StartCrawlJobParams(url="https://example.com")
    second = StartCrawlJobParams(url="https://example.com")

    first.include_patterns.append("/products/*")
    first.exclude_patterns.append("/admin/*")

    assert second.include_patterns == []
    assert second.exclude_patterns == []


def test_hyper_agent_output_actions_are_not_shared():
    first = HyperAgentOutput()
    second = HyperAgentOutput()

    first.actions.append({"action": "click"})

    assert second.actions == []


def test_fetch_browser_options_solve_captchas_is_bool():
    options = FetchBrowserOptions(solve_captchas=True)

    assert options.solve_captchas is True
