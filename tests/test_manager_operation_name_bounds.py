import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.async_manager.crawl as async_crawl_module
import hyperbrowser.client.managers.async_manager.extract as async_extract_module
import hyperbrowser.client.managers.sync_manager.crawl as sync_crawl_module
import hyperbrowser.client.managers.sync_manager.extract as sync_extract_module


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
        sync_extract_module, "wait_for_job_result", fake_wait_for_job_result
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
            "wait_for_job_result_async",
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
