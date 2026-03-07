import time

from tests.helpers.config import create_client, make_test_name
from tests.helpers.errors import expect_hyperbrowser_error
from tests.helpers.http import fetch_signed_url
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()


def _next_watch_event(watch, *, route="ws", cursor=None):
    for event in watch.events(route=route, cursor=cursor):
        if event.type == "event":
            return event.event
    raise RuntimeError("watch stream ended before an event was received")


def _wait_for_watch_buffer_rollover(watch, *, attempts=20, delay_seconds=0.1):
    for _ in range(attempts):
        refreshed = watch.refresh()
        if refreshed.current.oldest_seq > 1:
            return refreshed
        time.sleep(delay_seconds)
    raise RuntimeError("watch buffer did not roll over before timeout")


def test_sandbox_files_e2e():
    sandbox = None
    base_dir = f"/tmp/{make_test_name('py-sdk-files')}"

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-files"))
        wait_for_runtime_ready(sandbox)

        assert sandbox.files.exists(f"{base_dir}/missing.txt") is False

        result = sandbox.files.mkdir(base_dir, parents=True)
        assert result.path == base_dir

        sandbox.files.write_text(f"{base_dir}/hello.txt", "hello from sdk files")
        content = sandbox.files.read_text(f"{base_dir}/hello.txt")
        assert content == "hello from sdk files"

        chunk = sandbox.files.read_text(f"{base_dir}/hello.txt", offset=6, length=4)
        assert chunk == "from"

        result = sandbox.files.read(
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
        sandbox.files.write_bytes(f"{base_dir}/bytes.bin", source)
        content = sandbox.files.read_bytes(f"{base_dir}/bytes.bin")
        assert content == source

        stat = sandbox.files.stat(f"{base_dir}/hello.txt")
        assert stat.name == "hello.txt"

        listing = sandbox.files.list(base_dir)
        assert any(entry.name == "hello.txt" for entry in listing.entries)

        uploaded = sandbox.files.upload(f"{base_dir}/upload.txt", "uploaded from sdk")
        assert uploaded.bytes_written > 0

        downloaded = sandbox.files.download(f"{base_dir}/upload.txt")
        assert downloaded.decode("utf-8") == "uploaded from sdk"

        moved = sandbox.files.move(
            source=f"{base_dir}/hello.txt",
            destination=f"{base_dir}/hello-moved.txt",
        )
        assert moved.to == f"{base_dir}/hello-moved.txt"

        copied = sandbox.files.copy(
            source=f"{base_dir}/hello-moved.txt",
            destination=f"{base_dir}/hello-copy.txt",
        )
        assert copied.to == f"{base_dir}/hello-copy.txt"

        sandbox.files.chmod(path=f"{base_dir}/hello-copy.txt", mode="0640")
        stat = sandbox.files.stat(f"{base_dir}/hello-copy.txt")
        assert "640" in stat.mode

        try:
            expect_hyperbrowser_error(
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
            stat = sandbox.files.stat(f"{base_dir}/hello-copy.txt")
            assert stat.name == "hello-copy.txt"

        watch = sandbox.files.watch(base_dir, recursive=False)
        try:
            sandbox.files.write_text(f"{base_dir}/watch.txt", "watch me")
            event = _next_watch_event(watch, route="stream")
            assert "watch.txt" in event.path

            fetched = sandbox.files.get_watch(watch.id, True)
            assert fetched.id == watch.id
            assert fetched.current.path == base_dir
        finally:
            watch.stop()

        watch = sandbox.files.watch(base_dir, recursive=False)
        try:
            sandbox.files.write_text(f"{base_dir}/watch-refresh-1.txt", "one")
            refreshed = watch.refresh(True)
            assert refreshed.current.last_seq > 0
            assert refreshed.current.oldest_seq > 0
            assert any(
                "watch-refresh-1.txt" in event.path
                for event in (refreshed.current.events or [])
            )

            sandbox.files.write_text(f"{base_dir}/watch-refresh-2.txt", "two")
            event = _next_watch_event(
                watch,
                route="ws",
                cursor=refreshed.current.last_seq,
            )
            assert "watch-refresh-2.txt" in event.path
            assert watch.current.last_seq >= event.seq
        finally:
            watch.stop()

        watch = sandbox.files.watch(base_dir, recursive=False)
        try:
            burst = sandbox.exec(
                {
                    "command": "bash",
                    "args": [
                        "-lc",
                        f'for i in $(seq 1 1200); do echo x > "{base_dir}/overflow-$i.txt"; rm -f "{base_dir}/overflow-$i.txt"; done',
                    ],
                }
            )
            assert burst.exit_code == 0

            rolled = _wait_for_watch_buffer_rollover(watch)
            assert rolled.current.oldest_seq > 1

            expect_hyperbrowser_error(
                "watch replay window expired",
                lambda: next(watch.events(route="ws", cursor=0)),
                status_code=410,
                code="replay_window_expired",
                service="runtime",
                retryable=False,
                message_includes="Replay window expired",
            )
        finally:
            watch.stop()

        upload = sandbox.files.upload_url(
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

        uploaded_body = sandbox.files.read_text(f"{base_dir}/presign-upload.txt")
        assert uploaded_body == "presigned upload body"

        download = sandbox.files.download_url(
            f"{base_dir}/presign-upload.txt",
            one_time=True,
        )
        assert download.path == f"{base_dir}/presign-upload.txt"
        assert download.method == "GET"

        download_response = fetch_signed_url(download.url, method=download.method)
        assert download_response.status_code == 200
        assert download_response.text == "presigned upload body"

        deleted_file = sandbox.files.delete(f"{base_dir}/hello-copy.txt")
        assert deleted_file.path == f"{base_dir}/hello-copy.txt"

        deleted_dir = sandbox.files.delete(base_dir, recursive=True)
        assert deleted_dir.path == base_dir
        assert sandbox.files.exists(base_dir) is False

        expect_hyperbrowser_error(
            "missing file read",
            lambda: sandbox.files.read_text(f"{base_dir}/still-missing.txt"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )

        expect_hyperbrowser_error(
            "missing file delete",
            lambda: sandbox.files.delete(f"{base_dir}/still-missing.txt"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )
    finally:
        stop_sandbox_if_running(sandbox)
