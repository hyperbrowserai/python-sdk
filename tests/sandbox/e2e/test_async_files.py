import asyncio

import pytest

from hyperbrowser import AsyncHyperbrowser

from tests.helpers.config import make_test_name
from tests.helpers.errors import expect_hyperbrowser_error_async
from tests.helpers.http import fetch_signed_url
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running_async,
    wait_for_runtime_ready_async,
)


async def _next_watch_event(watch, *, route="ws", cursor=None):
    async for event in watch.events(route=route, cursor=cursor):
        if event.type == "event":
            return event.event
    raise RuntimeError("watch stream ended before an event was received")


async def _wait_for_watch_buffer_rollover(watch, *, attempts=20, delay_seconds=0.1):
    for _ in range(attempts):
        refreshed = await watch.refresh()
        if refreshed.current.oldest_seq > 1:
            return refreshed
        await asyncio.sleep(delay_seconds)
    raise RuntimeError("watch buffer did not roll over before timeout")


@pytest.mark.anyio
async def test_async_sandbox_files_e2e():
    client = AsyncHyperbrowser()
    sandbox = None
    base_dir = f"/tmp/{make_test_name('py-async-files')}"

    try:
        sandbox = await client.sandboxes.create(default_sandbox_params("py-async-files"))
        await wait_for_runtime_ready_async(sandbox)

        assert await sandbox.files.exists(f"{base_dir}/missing.txt") is False

        result = await sandbox.files.mkdir(base_dir, parents=True)
        assert result.path == base_dir

        await sandbox.files.write_text(f"{base_dir}/hello.txt", "hello from sdk files")
        content = await sandbox.files.read_text(f"{base_dir}/hello.txt")
        assert content == "hello from sdk files"

        chunk = await sandbox.files.read_text(
            f"{base_dir}/hello.txt", offset=6, length=4
        )
        assert chunk == "from"

        result = await sandbox.files.read(
            f"{base_dir}/hello.txt",
            offset=0,
            length=5,
            encoding="utf8",
        )
        assert result.content == "hello"
        assert result.encoding == "utf8"
        assert result.bytes_read == 5
        assert result.truncated is True

        source = bytes([0, 1, 2, 3, 4])
        await sandbox.files.write_bytes(f"{base_dir}/bytes.bin", source)
        content = await sandbox.files.read_bytes(f"{base_dir}/bytes.bin")
        assert content == source

        stat = await sandbox.files.stat(f"{base_dir}/hello.txt")
        assert stat.name == "hello.txt"

        listing = await sandbox.files.list(base_dir)
        assert any(entry.name == "hello.txt" for entry in listing.entries)

        uploaded = await sandbox.files.upload(f"{base_dir}/upload.txt", "uploaded from sdk")
        assert uploaded.bytes_written > 0

        downloaded = await sandbox.files.download(f"{base_dir}/upload.txt")
        assert downloaded.decode("utf-8") == "uploaded from sdk"

        moved = await sandbox.files.move(
            source=f"{base_dir}/hello.txt",
            destination=f"{base_dir}/hello-moved.txt",
        )
        assert moved.to == f"{base_dir}/hello-moved.txt"

        copied = await sandbox.files.copy(
            source=f"{base_dir}/hello-moved.txt",
            destination=f"{base_dir}/hello-copy.txt",
        )
        assert copied.to == f"{base_dir}/hello-copy.txt"

        await sandbox.files.chmod(path=f"{base_dir}/hello-copy.txt", mode="0640")
        stat = await sandbox.files.stat(f"{base_dir}/hello-copy.txt")
        assert "640" in stat.mode

        try:
            await expect_hyperbrowser_error_async(
                "file chown",
                lambda: sandbox.files.chown(
                    path=f"{base_dir}/hello-copy.txt",
                    uid=0,
                    gid=0,
                ),
                status_code=400,
                service="runtime",
                retryable=False,
                message_includes_any=["operation", "permission"],
            )
        except AssertionError as error:
            if "expected HyperbrowserError, but call succeeded" not in str(error):
                raise
            stat = await sandbox.files.stat(f"{base_dir}/hello-copy.txt")
            assert stat.name == "hello-copy.txt"

        watch = await sandbox.files.watch(base_dir, recursive=False)
        try:
            await sandbox.files.write_text(f"{base_dir}/watch.txt", "watch me")
            event = await _next_watch_event(watch, route="stream")
            assert "watch.txt" in event.path

            fetched = await sandbox.files.get_watch(watch.id, True)
            assert fetched.id == watch.id
            assert fetched.current.path == base_dir
        finally:
            await watch.stop()

        watch = await sandbox.files.watch(base_dir, recursive=False)
        try:
            await sandbox.files.write_text(f"{base_dir}/watch-refresh-1.txt", "one")
            refreshed = await watch.refresh(True)
            assert refreshed.current.last_seq > 0
            assert refreshed.current.oldest_seq > 0
            assert any(
                "watch-refresh-1.txt" in event.path
                for event in (refreshed.current.events or [])
            )

            await sandbox.files.write_text(f"{base_dir}/watch-refresh-2.txt", "two")
            event = await _next_watch_event(
                watch,
                route="ws",
                cursor=refreshed.current.last_seq,
            )
            assert "watch-refresh-2.txt" in event.path
            assert watch.current.last_seq >= event.seq
        finally:
            await watch.stop()

        watch = await sandbox.files.watch(base_dir, recursive=False)
        try:
            burst = await sandbox.exec(
                {
                    "command": "bash",
                    "args": [
                        "-lc",
                        f'for i in $(seq 1 1200); do echo x > "{base_dir}/overflow-$i.txt"; rm -f "{base_dir}/overflow-$i.txt"; done',
                    ],
                }
            )
            assert burst.exit_code == 0

            rolled = await _wait_for_watch_buffer_rollover(watch)
            assert rolled.current.oldest_seq > 1

            await expect_hyperbrowser_error_async(
                "watch replay window expired",
                lambda: anext(watch.events(route="ws", cursor=0)),
                status_code=410,
                code="replay_window_expired",
                service="runtime",
                retryable=False,
                message_includes="Replay window expired",
            )
        finally:
            await watch.stop()

        upload = await sandbox.files.upload_url(
            f"{base_dir}/presign-upload.txt",
            one_time=True,
        )
        assert upload.path == f"{base_dir}/presign-upload.txt"
        assert upload.url
        assert upload.method == "PUT"

        upload_response = fetch_signed_url(
            upload.url,
            method=upload.method,
            body="presigned upload body",
        )
        assert upload_response.status_code == 200

        uploaded_body = await sandbox.files.read_text(f"{base_dir}/presign-upload.txt")
        assert uploaded_body == "presigned upload body"

        download = await sandbox.files.download_url(
            f"{base_dir}/presign-upload.txt",
            one_time=True,
        )
        assert download.path == f"{base_dir}/presign-upload.txt"
        assert download.method == "GET"

        download_response = fetch_signed_url(download.url, method=download.method)
        assert download_response.status_code == 200
        assert download_response.text == "presigned upload body"

        deleted_file = await sandbox.files.delete(f"{base_dir}/hello-copy.txt")
        assert deleted_file.path == f"{base_dir}/hello-copy.txt"

        deleted_dir = await sandbox.files.delete(base_dir, recursive=True)
        assert deleted_dir.path == base_dir
        assert await sandbox.files.exists(base_dir) is False

        await expect_hyperbrowser_error_async(
            "missing file read",
            lambda: sandbox.files.read_text(f"{base_dir}/still-missing.txt"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )

        await expect_hyperbrowser_error_async(
            "missing file delete",
            lambda: sandbox.files.delete(f"{base_dir}/still-missing.txt"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await client.close()
