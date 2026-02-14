import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.async_manager.agents.browser_use as async_browser_use_module
import hyperbrowser.client.managers.async_manager.agents.claude_computer_use as async_claude_module
import hyperbrowser.client.managers.async_manager.agents.cua as async_cua_module
import hyperbrowser.client.managers.async_manager.agents.gemini_computer_use as async_gemini_module
import hyperbrowser.client.managers.async_manager.agents.hyper_agent as async_hyper_agent_module
import hyperbrowser.client.managers.async_manager.web.batch_fetch as async_batch_fetch_module
import hyperbrowser.client.managers.async_manager.web.crawl as async_web_crawl_module
import hyperbrowser.client.managers.async_manager.crawl as async_crawl_module
import hyperbrowser.client.managers.async_manager.extract as async_extract_module
import hyperbrowser.client.managers.sync_manager.agents.browser_use as sync_browser_use_module
import hyperbrowser.client.managers.sync_manager.agents.claude_computer_use as sync_claude_module
import hyperbrowser.client.managers.sync_manager.agents.cua as sync_cua_module
import hyperbrowser.client.managers.sync_manager.agents.gemini_computer_use as sync_gemini_module
import hyperbrowser.client.managers.sync_manager.agents.hyper_agent as sync_hyper_agent_module
import hyperbrowser.client.managers.sync_manager.web.batch_fetch as sync_batch_fetch_module
import hyperbrowser.client.managers.sync_manager.web.crawl as sync_web_crawl_module
import hyperbrowser.client.managers.sync_manager.crawl as sync_crawl_module
import hyperbrowser.client.managers.sync_manager.extract as sync_extract_module
import hyperbrowser.client.managers.sync_manager.scrape as sync_scrape_module
from hyperbrowser.client.polling import build_fetch_operation_name
import hyperbrowser.client.managers.async_manager.scrape as async_scrape_module


class _DummyClient:
    transport = None


def _assert_valid_operation_name(value: str) -> None:
    assert isinstance(value, str)
    assert value
    assert len(value) <= 200
    assert value == value.strip()
    assert not any(ord(character) < 32 or ord(character) == 127 for character in value)


def test_sync_extract_manager_bounds_operation_name(monkeypatch):
    manager = sync_extract_module.ExtractManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_wait_for_job_result(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        assert operation_name.startswith("extract job ")
        captured["operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_extract_module,
        "wait_for_job_result_with_defaults",
        fake_wait_for_job_result,
    )

    result = manager.start_and_wait(params=object())  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["operation_name"].endswith("...")


def test_sync_crawl_manager_bounds_operation_name_for_polling_and_pagination(
    monkeypatch,
):
    manager = sync_crawl_module.CrawlManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_collect_paginated_results(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["collect_operation_name"] = operation_name
        assert operation_name == captured["poll_operation_name"]

    monkeypatch.setattr(
        sync_crawl_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_crawl_module,
        "collect_paginated_results",
        fake_collect_paginated_results,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=True)  # type: ignore[arg-type]

    assert result.status == "completed"
    assert captured["poll_operation_name"].startswith("crawl job ")
    assert captured["poll_operation_name"].endswith("...")


def test_sync_crawl_manager_bounds_operation_name_for_fetch_retry_path(monkeypatch):
    manager = sync_crawl_module.CrawlManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_retry_operation(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["fetch_operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_crawl_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_crawl_module,
        "retry_operation",
        fake_retry_operation,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=False)  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["fetch_operation_name"] == build_fetch_operation_name(
        captured["poll_operation_name"]
    )


def test_async_extract_manager_bounds_operation_name(monkeypatch):
    async def run() -> None:
        manager = async_extract_module.ExtractManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_wait_for_job_result_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            assert operation_name.startswith("extract job ")
            captured["operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_extract_module,
            "wait_for_job_result_with_defaults_async",
            fake_wait_for_job_result_async,
        )

        result = await manager.start_and_wait(params=object())  # type: ignore[arg-type]

        assert result == {"ok": True}
        assert captured["operation_name"].endswith("...")

    asyncio.run(run())


def test_async_crawl_manager_bounds_operation_name_for_polling_and_pagination(
    monkeypatch,
):
    async def run() -> None:
        manager = async_crawl_module.CrawlManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_collect_paginated_results_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["collect_operation_name"] = operation_name
            assert operation_name == captured["poll_operation_name"]

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_crawl_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_crawl_module,
            "collect_paginated_results_async",
            fake_collect_paginated_results_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=True,
        )

        assert result.status == "completed"
        assert captured["poll_operation_name"].startswith("crawl job ")
        assert captured["poll_operation_name"].endswith("...")

    asyncio.run(run())


def test_async_crawl_manager_bounds_operation_name_for_fetch_retry_path(monkeypatch):
    async def run() -> None:
        manager = async_crawl_module.CrawlManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_retry_operation_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["fetch_operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_crawl_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_crawl_module,
            "retry_operation_async",
            fake_retry_operation_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=False,
        )

        assert result == {"ok": True}
        assert captured["fetch_operation_name"] == build_fetch_operation_name(
            captured["poll_operation_name"]
        )

    asyncio.run(run())


def test_sync_batch_fetch_manager_bounds_operation_name_for_fetch_retry_path(
    monkeypatch,
):
    manager = sync_batch_fetch_module.BatchFetchManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_retry_operation(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["fetch_operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_batch_fetch_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_batch_fetch_module,
        "retry_operation",
        fake_retry_operation,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=False)  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["fetch_operation_name"] == build_fetch_operation_name(
        captured["poll_operation_name"]
    )


def test_async_batch_fetch_manager_bounds_operation_name_for_fetch_retry_path(
    monkeypatch,
):
    async def run() -> None:
        manager = async_batch_fetch_module.BatchFetchManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_retry_operation_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["fetch_operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_batch_fetch_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_batch_fetch_module,
            "retry_operation_async",
            fake_retry_operation_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=False,
        )

        assert result == {"ok": True}
        assert captured["fetch_operation_name"] == build_fetch_operation_name(
            captured["poll_operation_name"]
        )

    asyncio.run(run())


def test_sync_batch_fetch_manager_bounds_operation_name_for_paginated_path(
    monkeypatch,
):
    manager = sync_batch_fetch_module.BatchFetchManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_collect_paginated_results(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["collect_operation_name"] = operation_name

    monkeypatch.setattr(
        sync_batch_fetch_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_batch_fetch_module,
        "collect_paginated_results",
        fake_collect_paginated_results,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=True)  # type: ignore[arg-type]

    assert result.status == "completed"
    assert captured["collect_operation_name"] == captured["poll_operation_name"]


def test_async_batch_fetch_manager_bounds_operation_name_for_paginated_path(
    monkeypatch,
):
    async def run() -> None:
        manager = async_batch_fetch_module.BatchFetchManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_collect_paginated_results_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["collect_operation_name"] = operation_name

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_batch_fetch_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_batch_fetch_module,
            "collect_paginated_results_async",
            fake_collect_paginated_results_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=True,
        )

        assert result.status == "completed"
        assert captured["collect_operation_name"] == captured["poll_operation_name"]

    asyncio.run(run())


def test_sync_web_crawl_manager_bounds_operation_name_for_fetch_retry_path(monkeypatch):
    manager = sync_web_crawl_module.WebCrawlManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_retry_operation(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["fetch_operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_web_crawl_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_web_crawl_module,
        "retry_operation",
        fake_retry_operation,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=False)  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["fetch_operation_name"] == build_fetch_operation_name(
        captured["poll_operation_name"]
    )


def test_async_web_crawl_manager_bounds_operation_name_for_fetch_retry_path(
    monkeypatch,
):
    async def run() -> None:
        manager = async_web_crawl_module.WebCrawlManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_retry_operation_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["fetch_operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_web_crawl_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_web_crawl_module,
            "retry_operation_async",
            fake_retry_operation_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=False,
        )

        assert result == {"ok": True}
        assert captured["fetch_operation_name"] == build_fetch_operation_name(
            captured["poll_operation_name"]
        )

    asyncio.run(run())


def test_sync_web_crawl_manager_bounds_operation_name_for_paginated_path(monkeypatch):
    manager = sync_web_crawl_module.WebCrawlManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_collect_paginated_results(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["collect_operation_name"] = operation_name

    monkeypatch.setattr(
        sync_web_crawl_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_web_crawl_module,
        "collect_paginated_results",
        fake_collect_paginated_results,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=True)  # type: ignore[arg-type]

    assert result.status == "completed"
    assert captured["collect_operation_name"] == captured["poll_operation_name"]


def test_async_web_crawl_manager_bounds_operation_name_for_paginated_path(monkeypatch):
    async def run() -> None:
        manager = async_web_crawl_module.WebCrawlManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_collect_paginated_results_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["collect_operation_name"] = operation_name

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_web_crawl_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_web_crawl_module,
            "collect_paginated_results_async",
            fake_collect_paginated_results_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=True,
        )

        assert result.status == "completed"
        assert captured["collect_operation_name"] == captured["poll_operation_name"]

    asyncio.run(run())


def test_sync_batch_scrape_manager_bounds_operation_name_for_fetch_retry_path(
    monkeypatch,
):
    manager = sync_scrape_module.BatchScrapeManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_retry_operation(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["fetch_operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_scrape_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_scrape_module,
        "retry_operation",
        fake_retry_operation,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=False)  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["fetch_operation_name"] == build_fetch_operation_name(
        captured["poll_operation_name"]
    )


def test_async_batch_scrape_manager_bounds_operation_name_for_fetch_retry_path(
    monkeypatch,
):
    async def run() -> None:
        manager = async_scrape_module.BatchScrapeManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_retry_operation_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["fetch_operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_scrape_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_scrape_module,
            "retry_operation_async",
            fake_retry_operation_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=False,
        )

        assert result == {"ok": True}
        assert captured["fetch_operation_name"] == build_fetch_operation_name(
            captured["poll_operation_name"]
        )

    asyncio.run(run())


def test_sync_batch_scrape_manager_bounds_operation_name_for_paginated_path(
    monkeypatch,
):
    manager = sync_scrape_module.BatchScrapeManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_poll_until_terminal_status(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["poll_operation_name"] = operation_name
        return "completed"

    def fake_collect_paginated_results(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["collect_operation_name"] = operation_name

    monkeypatch.setattr(
        sync_scrape_module,
        "poll_until_terminal_status",
        fake_poll_until_terminal_status,
    )
    monkeypatch.setattr(
        sync_scrape_module,
        "collect_paginated_results",
        fake_collect_paginated_results,
    )

    result = manager.start_and_wait(params=object(), return_all_pages=True)  # type: ignore[arg-type]

    assert result.status == "completed"
    assert captured["collect_operation_name"] == captured["poll_operation_name"]


def test_async_batch_scrape_manager_bounds_operation_name_for_paginated_path(
    monkeypatch,
):
    async def run() -> None:
        manager = async_scrape_module.BatchScrapeManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_poll_until_terminal_status_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["poll_operation_name"] = operation_name
            return "completed"

        async def fake_collect_paginated_results_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["collect_operation_name"] = operation_name

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_scrape_module,
            "poll_until_terminal_status_async",
            fake_poll_until_terminal_status_async,
        )
        monkeypatch.setattr(
            async_scrape_module,
            "collect_paginated_results_async",
            fake_collect_paginated_results_async,
        )

        result = await manager.start_and_wait(
            params=object(),  # type: ignore[arg-type]
            return_all_pages=True,
        )

        assert result.status == "completed"
        assert captured["collect_operation_name"] == captured["poll_operation_name"]

    asyncio.run(run())


def test_sync_browser_use_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    manager = sync_browser_use_module.BrowserUseManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_wait_for_job_result(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_browser_use_module,
        "wait_for_job_result_with_defaults",
        fake_wait_for_job_result,
    )

    result = manager.start_and_wait(params=object())  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["operation_name"].startswith("browser-use task job ")


def test_sync_cua_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    manager = sync_cua_module.CuaManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_wait_for_job_result(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_cua_module,
        "wait_for_job_result_with_defaults",
        fake_wait_for_job_result,
    )

    result = manager.start_and_wait(params=object())  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["operation_name"].startswith("CUA task job ")


def test_async_browser_use_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    async def run() -> None:
        manager = async_browser_use_module.BrowserUseManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_wait_for_job_result_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_browser_use_module,
            "wait_for_job_result_with_defaults_async",
            fake_wait_for_job_result_async,
        )

        result = await manager.start_and_wait(params=object())  # type: ignore[arg-type]

        assert result == {"ok": True}
        assert captured["operation_name"].startswith("browser-use task job ")

    asyncio.run(run())


def test_async_cua_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    async def run() -> None:
        manager = async_cua_module.CuaManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_wait_for_job_result_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_cua_module,
            "wait_for_job_result_with_defaults_async",
            fake_wait_for_job_result_async,
        )

        result = await manager.start_and_wait(params=object())  # type: ignore[arg-type]

        assert result == {"ok": True}
        assert captured["operation_name"].startswith("CUA task job ")

    asyncio.run(run())


def test_sync_scrape_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    manager = sync_scrape_module.ScrapeManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_wait_for_job_result(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_scrape_module,
        "wait_for_job_result_with_defaults",
        fake_wait_for_job_result,
    )

    result = manager.start_and_wait(params=object())  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["operation_name"].startswith("scrape job ")


def test_async_scrape_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    async def run() -> None:
        manager = async_scrape_module.ScrapeManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_wait_for_job_result_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_scrape_module,
            "wait_for_job_result_with_defaults_async",
            fake_wait_for_job_result_async,
        )

        result = await manager.start_and_wait(params=object())  # type: ignore[arg-type]

        assert result == {"ok": True}
        assert captured["operation_name"].startswith("scrape job ")

    asyncio.run(run())


def test_sync_claude_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    manager = sync_claude_module.ClaudeComputerUseManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_wait_for_job_result(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_claude_module,
        "wait_for_job_result_with_defaults",
        fake_wait_for_job_result,
    )

    result = manager.start_and_wait(params=object())  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["operation_name"].startswith("Claude Computer Use task job ")


def test_async_claude_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    async def run() -> None:
        manager = async_claude_module.ClaudeComputerUseManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_wait_for_job_result_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_claude_module,
            "wait_for_job_result_with_defaults_async",
            fake_wait_for_job_result_async,
        )

        result = await manager.start_and_wait(params=object())  # type: ignore[arg-type]

        assert result == {"ok": True}
        assert captured["operation_name"].startswith("Claude Computer Use task job ")

    asyncio.run(run())


def test_sync_gemini_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    manager = sync_gemini_module.GeminiComputerUseManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_wait_for_job_result(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_gemini_module,
        "wait_for_job_result_with_defaults",
        fake_wait_for_job_result,
    )

    result = manager.start_and_wait(params=object())  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["operation_name"].startswith("Gemini Computer Use task job ")


def test_async_gemini_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    async def run() -> None:
        manager = async_gemini_module.GeminiComputerUseManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_wait_for_job_result_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_gemini_module,
            "wait_for_job_result_with_defaults_async",
            fake_wait_for_job_result_async,
        )

        result = await manager.start_and_wait(params=object())  # type: ignore[arg-type]

        assert result == {"ok": True}
        assert captured["operation_name"].startswith("Gemini Computer Use task job ")

    asyncio.run(run())


def test_sync_hyper_agent_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    manager = sync_hyper_agent_module.HyperAgentManager(_DummyClient())
    long_job_id = " \n" + ("x" * 500) + "\t"
    captured = {}

    monkeypatch.setattr(
        manager,
        "start",
        lambda params: SimpleNamespace(job_id=long_job_id),
    )

    def fake_wait_for_job_result(**kwargs):
        operation_name = kwargs["operation_name"]
        _assert_valid_operation_name(operation_name)
        captured["operation_name"] = operation_name
        return {"ok": True}

    monkeypatch.setattr(
        sync_hyper_agent_module,
        "wait_for_job_result_with_defaults",
        fake_wait_for_job_result,
    )

    result = manager.start_and_wait(params=object())  # type: ignore[arg-type]

    assert result == {"ok": True}
    assert captured["operation_name"].startswith("HyperAgent task ")


def test_async_hyper_agent_manager_bounds_operation_name_in_wait_helper(monkeypatch):
    async def run() -> None:
        manager = async_hyper_agent_module.HyperAgentManager(_DummyClient())
        long_job_id = " \n" + ("x" * 500) + "\t"
        captured = {}

        async def fake_start(params):
            return SimpleNamespace(job_id=long_job_id)

        async def fake_wait_for_job_result_async(**kwargs):
            operation_name = kwargs["operation_name"]
            _assert_valid_operation_name(operation_name)
            captured["operation_name"] = operation_name
            return {"ok": True}

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(
            async_hyper_agent_module,
            "wait_for_job_result_with_defaults_async",
            fake_wait_for_job_result_async,
        )

        result = await manager.start_and_wait(params=object())  # type: ignore[arg-type]

        assert result == {"ok": True}
        assert captured["operation_name"].startswith("HyperAgent task ")

    asyncio.run(run())
