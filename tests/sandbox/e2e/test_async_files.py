import asyncio

import pytest

from hyperbrowser.models import SandboxExecParams, SandboxFileWriteEntry

from tests.helpers.config import create_async_client, make_test_name
from tests.helpers.errors import expect_hyperbrowser_error_async
from tests.helpers.http import fetch_signed_url
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running_async,
    wait_for_runtime_ready_async,
)


def _read_stream_text(stream) -> str:
    return stream.read().decode("utf-8")


def _bash_exec(command: str, run_as: str = "root") -> SandboxExecParams:
    return SandboxExecParams(command="bash", args=["-lc", command], run_as=run_as)


async def _await_future(future: asyncio.Future, timeout: float = 10.0):
    return await asyncio.wait_for(future, timeout=timeout)


async def _create_parent_symlink_escape_fixture(sandbox, base_dir: str, name: str):
    allowed_dir = f"{base_dir}/{name}"
    outside_dir = f"/var/tmp/{make_test_name(name)}"
    outside_file = f"{outside_dir}/secret.txt"
    link_dir = f"{allowed_dir}/evil"
    escaped_file = f"{link_dir}/secret.txt"
    setup = await sandbox.exec(
        _bash_exec(
            " && ".join(
                [
                    f'mkdir -p "{allowed_dir}"',
                    f'mkdir -p "{outside_dir}"',
                    f'printf "outside secret" > "{outside_file}"',
                    f'ln -sfn "{outside_dir}" "{link_dir}"',
                ]
            )
        )
    )
    assert setup.exit_code == 0
    return {
        "allowed_dir": allowed_dir,
        "outside_dir": outside_dir,
        "outside_file": outside_file,
        "link_dir": link_dir,
        "escaped_file": escaped_file,
    }


@pytest.mark.anyio
async def test_async_sandbox_files_e2e():
    client = create_async_client()
    sandbox = None
    base_dir = f"/tmp/{make_test_name('py-async-files')}"

    try:
        sandbox = await client.sandboxes.create(
            default_sandbox_params("py-async-files")
        )
        await wait_for_runtime_ready_async(sandbox)
        files = sandbox.files.with_run_as("root")

        assert await files.exists(f"{base_dir}/missing.txt") is False

        path = f"{base_dir}/dirs/root"
        assert await files.make_dir(path) is True
        assert await files.make_dir(path) is False

        info_path = f"{base_dir}/info/hello.txt"
        await files.write_text(info_path, "hello from sdk files")
        info = await files.get_info(info_path)
        assert info.name == "hello.txt"
        assert info.path == info_path
        assert info.type == "file"
        assert info.size == len("hello from sdk files")
        assert info.mode == 0o644
        assert info.permissions == "-rw-r--r--"
        assert info.owner
        assert info.group
        assert info.modified_time is not None

        list_dir = f"{base_dir}/list"
        await files.make_dir(f"{list_dir}/nested/inner", parents=True)
        await files.write_text(f"{list_dir}/root.txt", "root")
        await files.write_text(f"{list_dir}/nested/child.txt", "child")
        await files.write_text(f"{list_dir}/nested/inner/grandchild.txt", "grandchild")

        depth_one = await files.list(list_dir, depth=1)
        assert [entry.name for entry in depth_one] == ["nested", "root.txt"]
        assert [entry.type for entry in depth_one] == ["dir", "file"]

        depth_two = await files.list(list_dir, depth=2)
        assert [entry.path for entry in depth_two] == [
            f"{list_dir}/nested",
            f"{list_dir}/nested/child.txt",
            f"{list_dir}/nested/inner",
            f"{list_dir}/root.txt",
        ]

        symlink_dir = f"{base_dir}/list-symlink"
        target = f"{symlink_dir}/target.txt"
        link = f"{symlink_dir}/link.txt"
        await files.make_dir(symlink_dir)
        await files.write_text(target, "payload")
        result = await sandbox.exec(_bash_exec(f'ln -sfn "{target}" "{link}"'))
        assert result.exit_code == 0
        link_entry = next(
            entry
            for entry in await files.list(symlink_dir, depth=1)
            if entry.path == link
        )
        assert link_entry.symlink_target == target

        symlink_target = f"{base_dir}/symlink/target.txt"
        symlink_link = f"{base_dir}/symlink/link.txt"
        await files.write_text(symlink_target, "target")
        result = await sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/symlink" && ln -sfn "{symlink_target}" "{symlink_link}"'
            )
        )
        assert result.exit_code == 0
        assert (await files.get_info(symlink_link)).symlink_target == symlink_target

        broken_target = f"{base_dir}/symlink-broken/missing-target.txt"
        broken_link = f"{base_dir}/symlink-broken/link.txt"
        result = await sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/symlink-broken" && ln -sfn "{broken_target}" "{broken_link}"'
            )
        )
        assert result.exit_code == 0
        assert await files.exists(broken_link) is True
        assert (await files.get_info(broken_link)).symlink_target == broken_target

        read_path = f"{base_dir}/read/readme.txt"
        await files.write_text(read_path, "hello from sdk files")
        assert await files.read(read_path) == "hello from sdk files"
        assert await files.read(read_path, format="text", offset=6, length=4) == "from"
        assert await files.read(read_path, format="bytes") == b"hello from sdk files"
        assert await files.read(read_path, format="blob") == b"hello from sdk files"
        assert (
            _read_stream_text(await files.read(read_path, format="stream"))
            == "hello from sdk files"
        )

        single = await files.write(f"{base_dir}/write/single.txt", "single file")
        assert single.name == "single.txt"
        assert single.path == f"{base_dir}/write/single.txt"
        assert await files.read_text(single.path) == "single file"

        batch = await files.write(
            [
                SandboxFileWriteEntry(
                    path=f"{base_dir}/write/batch-a.txt",
                    data="batch-a",
                ),
                SandboxFileWriteEntry(
                    path=f"{base_dir}/write/batch-b.bin",
                    data=bytes([1, 2, 3, 4]),
                ),
            ]
        )
        assert [entry.name for entry in batch] == ["batch-a.txt", "batch-b.bin"]
        assert await files.read_text(f"{base_dir}/write/batch-a.txt") == "batch-a"
        assert await files.read_bytes(f"{base_dir}/write/batch-b.bin") == bytes(
            [1, 2, 3, 4]
        )

        text_path = f"{base_dir}/write-options/text.txt"
        await files.write_text(text_path, "hello", mode="0640")
        await files.write_text(text_path, " world", append=True)
        assert await files.read_text(text_path) == "hello world"
        assert (await files.get_info(text_path)).mode == 0o640

        bytes_path = f"{base_dir}/write-options/bytes.bin"
        await files.write_bytes(bytes_path, bytes([1, 2]), mode="0600")
        await files.write_bytes(bytes_path, bytes([3]), append=True)
        assert await files.read_bytes(bytes_path) == bytes([1, 2, 3])

        transfer_path = f"{base_dir}/transfer/upload.txt"
        uploaded = await files.upload(transfer_path, "uploaded from sdk")
        assert uploaded.bytes_written > 0
        assert (await files.download(transfer_path)).decode(
            "utf-8"
        ) == "uploaded from sdk"

        file_path = f"{base_dir}/rename/hello.txt"
        renamed_path = f"{base_dir}/rename/hello-renamed.txt"
        await files.write_text(file_path, "rename me")
        renamed = await files.rename(file_path, renamed_path)
        assert renamed.path == renamed_path
        assert await files.exists(file_path) is False
        assert await files.read_text(renamed_path) == "rename me"

        link_path = f"{base_dir}/rename/hello-link.txt"
        copied_link_path = f"{base_dir}/rename/hello-link-copy.txt"
        renamed_link_path = f"{base_dir}/rename/hello-link-renamed.txt"
        result = await sandbox.exec(
            _bash_exec(f'ln -sfn "{renamed_path}" "{link_path}"')
        )
        assert result.exit_code == 0
        copied_link = await files.copy(source=link_path, destination=copied_link_path)
        assert copied_link.path == copied_link_path
        assert (await files.get_info(copied_link_path)).symlink_target == renamed_path
        renamed_link = await files.rename(copied_link_path, renamed_link_path)
        assert renamed_link.path == renamed_link_path
        assert (await files.get_info(renamed_link_path)).symlink_target == renamed_path

        target_dir = f"{base_dir}/rename-dir/target-dir"
        link_dir = f"{base_dir}/rename-dir/link-dir"
        renamed_link_dir = f"{base_dir}/rename-dir/link-dir-renamed"
        await files.make_dir(target_dir)
        await files.write_text(f"{target_dir}/child.txt", "child")
        result = await sandbox.exec(_bash_exec(f'ln -sfn "{target_dir}" "{link_dir}"'))
        assert result.exit_code == 0
        renamed = await files.rename(link_dir, renamed_link_dir)
        assert renamed.path == renamed_link_dir
        assert (await files.get_info(renamed_link_dir)).symlink_target == target_dir
        assert [
            entry.path for entry in await files.list(renamed_link_dir, depth=1)
        ] == [f"{target_dir}/child.txt"]

        source_dir = f"{base_dir}/copy-tree/source"
        nested_dir = f"{source_dir}/nested"
        nested_target = f"{nested_dir}/target.txt"
        destination_dir = f"{base_dir}/copy-tree/destination"
        await files.make_dir(nested_dir)
        await files.write_text(nested_target, "payload")
        result = await sandbox.exec(
            _bash_exec(f'cd "{nested_dir}" && ln -sfn "target.txt" "link.txt"')
        )
        assert result.exit_code == 0
        await files.copy(source=source_dir, destination=destination_dir, recursive=True)
        copied_target = f"{destination_dir}/nested/target.txt"
        copied_link = f"{destination_dir}/nested/link.txt"
        assert await files.read_text(copied_target) == "payload"
        assert (await files.get_info(copied_link)).symlink_target == copied_target

        loop_dir = f"{base_dir}/loop-list"
        loop_nested_dir = f"{loop_dir}/nested"
        await files.make_dir(loop_nested_dir)
        await files.write_text(f"{loop_nested_dir}/child.txt", "payload")
        result = await sandbox.exec(
            _bash_exec(f'cd "{loop_nested_dir}" && ln -sfn .. loop')
        )
        assert result.exit_code == 0
        loop_entries = await files.list(loop_dir, depth=4)
        loop_paths = [entry.path for entry in loop_entries]
        assert f"{loop_nested_dir}/loop" in loop_paths
        assert not any("/loop/" in path for path in loop_paths)
        assert (
            await files.get_info(f"{loop_nested_dir}/loop")
        ).symlink_target == loop_dir

        source_dir = f"{base_dir}/loop-copy/source"
        nested_dir = f"{source_dir}/nested"
        await files.make_dir(nested_dir)
        await files.write_text(f"{nested_dir}/child.txt", "payload")
        result = await sandbox.exec(_bash_exec(f'cd "{nested_dir}" && ln -sfn .. loop'))
        assert result.exit_code == 0
        destination_dir = f"{base_dir}/loop-copy/destination"
        await files.copy(source=source_dir, destination=destination_dir, recursive=True)
        copied_loop = f"{destination_dir}/nested/loop"
        assert (await files.get_info(copied_loop)).symlink_target == destination_dir
        assert not any(
            "/loop/" in entry.path
            for entry in await files.list(destination_dir, depth=4)
        )

        source = f"{base_dir}/copy-overwrite/source.txt"
        existing_target = f"{base_dir}/copy-overwrite/existing-target.txt"
        destination_link = f"{base_dir}/copy-overwrite/destination-link.txt"
        await files.write_text(source, "source payload")
        await files.write_text(existing_target, "existing target")
        result = await sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/copy-overwrite" && ln -sfn "{existing_target}" "{destination_link}"'
            )
        )
        assert result.exit_code == 0
        await files.copy(source=source, destination=destination_link, overwrite=True)
        assert await files.read_text(destination_link) == "source payload"
        assert await files.read_text(existing_target) == "existing target"
        assert (await files.get_info(destination_link)).symlink_target is None

        move_source = f"{base_dir}/move-overwrite/source.txt"
        move_existing_target = f"{base_dir}/move-overwrite/existing-target.txt"
        move_destination_link = f"{base_dir}/move-overwrite/destination-link.txt"
        await files.write_text(move_source, "move source payload")
        await files.write_text(move_existing_target, "move existing target")
        result = await sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/move-overwrite" && ln -sfn "{move_existing_target}" "{move_destination_link}"'
            )
        )
        assert result.exit_code == 0
        await files.move(
            source=move_source,
            destination=move_destination_link,
            overwrite=True,
        )
        assert await files.read_text(move_destination_link) == "move source payload"
        assert await files.read_text(move_existing_target) == "move existing target"
        assert (await files.get_info(move_destination_link)).symlink_target is None
        assert await files.exists(move_source) is False

        chmod_path = f"{base_dir}/chmod/file.txt"
        await files.write_text(chmod_path, "chmod me")
        await files.chmod(path=chmod_path, mode="0640")
        assert (await files.get_info(chmod_path)).mode == 0o640
        try:
            await expect_hyperbrowser_error_async(
                "file chown",
                lambda: files.chown(path=chmod_path, uid=0, gid=0),
                status_code=400,
                service="runtime",
                retryable=False,
                message_includes_any=["operation", "permission"],
            )
        except AssertionError as error:
            if "expected HyperbrowserError, but call succeeded" not in str(error):
                raise
            assert (await files.get_info(chmod_path)).name == "file.txt"

        remove_path = f"{base_dir}/remove/file.txt"
        await files.write_text(remove_path, "remove me")
        await files.remove(remove_path)
        assert await files.exists(remove_path) is False
        await files.remove(remove_path)
        await files.remove(f"{base_dir}/remove", recursive=True)
        assert await files.exists(f"{base_dir}/remove") is False

        target = f"{base_dir}/remove-link/target.txt"
        link = f"{base_dir}/remove-link/link.txt"
        await files.write_text(target, "keep me")
        result = await sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/remove-link" && ln -sfn "{target}" "{link}"'
            )
        )
        assert result.exit_code == 0
        await files.remove(link)
        assert await files.exists(link) is False
        assert await files.read_text(target) == "keep me"

        target_dir = f"{base_dir}/remove-recursive/target-dir"
        target_file = f"{target_dir}/child.txt"
        link_dir = f"{base_dir}/remove-recursive/link-dir"
        await files.make_dir(target_dir)
        await files.write_text(target_file, "keep tree")
        result = await sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/remove-recursive" && ln -sfn "{target_dir}" "{link_dir}"'
            )
        )
        assert result.exit_code == 0
        await files.remove(link_dir, recursive=True)
        assert await files.exists(link_dir) is False
        assert await files.read_text(target_file) == "keep tree"

        link = f"{base_dir}/escape/file-link"
        result = await sandbox.exec(
            _bash_exec(f'mkdir -p "{base_dir}/escape" && ln -sfn /etc/hosts "{link}"')
        )
        assert result.exit_code == 0
        text = await files.read_text(link)
        assert "localhost" in text
        assert "localhost" in (await files.download(link)).decode("utf-8")

        fixture = await _create_parent_symlink_escape_fixture(
            sandbox, base_dir, "parent-escape-read"
        )
        assert await files.read_text(fixture["escaped_file"]) == "outside secret"
        assert (await files.download(fixture["escaped_file"])).decode(
            "utf-8"
        ) == "outside secret"
        assert [
            entry.path for entry in await files.list(fixture["link_dir"], depth=1)
        ] == [f"{fixture['outside_dir']}/secret.txt"]
        seen = asyncio.get_running_loop().create_future()

        async def on_parent_event(event):
            if (
                event.type in {"create", "write"}
                and event.name == "fresh.txt"
                and not seen.done()
            ):
                seen.set_result(event.name)

        handle = await files.watch_dir(fixture["link_dir"], on_parent_event)
        try:
            await files.write_text(
                f"{fixture['outside_dir']}/fresh.txt", "watch parent link"
            )
            assert await _await_future(seen) == "fresh.txt"
        finally:
            await handle.stop()

        fixture = await _create_parent_symlink_escape_fixture(
            sandbox, base_dir, "parent-escape-mutate"
        )
        info = await files.get_info(fixture["escaped_file"])
        assert info.type == "file"
        assert info.size == len("outside secret")
        copied = await files.copy(
            source=fixture["escaped_file"],
            destination=f"{base_dir}/parent-escape-mutate/copied.txt",
        )
        assert copied.path == f"{base_dir}/parent-escape-mutate/copied.txt"
        assert await files.read_text(copied.path) == "outside secret"
        renamed = await files.rename(
            fixture["escaped_file"],
            f"{base_dir}/parent-escape-mutate/renamed.txt",
        )
        assert renamed.path == f"{base_dir}/parent-escape-mutate/renamed.txt"
        assert await files.exists(fixture["outside_file"]) is False
        assert await files.read_text(renamed.path) == "outside secret"
        await files.write_text(fixture["escaped_file"], "remove me")
        await files.remove(fixture["escaped_file"])
        outside_read = await sandbox.exec(
            _bash_exec(
                f'if [ -e "{fixture["outside_file"]}" ]; then cat "{fixture["outside_file"]}"; else printf "__MISSING__"; fi'
            )
        )
        assert outside_read.exit_code == 0
        assert outside_read.stdout.strip() == "__MISSING__"

        target_dir = f"/var/tmp/{make_test_name('watch-outside-target')}"
        target_file = f"{target_dir}/child.txt"
        link = f"{base_dir}/escape/dir-link"
        result = await sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/escape" "{target_dir}" && printf "child" > "{target_file}" && ln -sfn "{target_dir}" "{link}"'
            )
        )
        assert result.exit_code == 0
        assert [entry.path for entry in await files.list(link, depth=1)] == [
            target_file
        ]
        seen = asyncio.get_running_loop().create_future()

        async def on_link_event(event):
            if (
                event.type in {"create", "write"}
                and event.name == "file.txt"
                and not seen.done()
            ):
                seen.set_result(event.name)

        handle = await files.watch_dir(link, on_link_event)
        try:
            await files.write_text(f"{target_dir}/file.txt", "watch through link")
            assert await _await_future(seen) == "file.txt"
        finally:
            await handle.stop()

        watch_dir = f"{base_dir}/watch"
        await files.make_dir(f"{watch_dir}/nested", parents=True)
        direct_future = asyncio.get_running_loop().create_future()
        recursive_future = asyncio.get_running_loop().create_future()

        async def on_direct(event):
            if (
                event.type == "write"
                and event.name == "direct.txt"
                and not direct_future.done()
            ):
                direct_future.set_result(event.name)

        async def on_recursive(event):
            if (
                event.type == "write"
                and event.name == "nested/recursive.txt"
                and not recursive_future.done()
            ):
                recursive_future.set_result(event.name)

        direct_handle = await files.watch_dir(watch_dir, on_direct)
        recursive_handle = await files.watch_dir(
            watch_dir,
            on_recursive,
            recursive=True,
        )
        try:
            await files.write_text(f"{watch_dir}/direct.txt", "watch me")
            await files.write_text(f"{watch_dir}/nested/recursive.txt", "watch me too")
            assert await _await_future(direct_future) == "direct.txt"
            assert await _await_future(recursive_future) == "nested/recursive.txt"
        finally:
            await direct_handle.stop()
            await recursive_handle.stop()

        await expect_hyperbrowser_error_async(
            "watch missing directory",
            lambda: files.watch_dir(f"{base_dir}/watch-missing", lambda event: None),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )

        invalid_file_path = f"{base_dir}/watch-invalid/file.txt"
        await files.write_text(invalid_file_path, "not a directory")
        await expect_hyperbrowser_error_async(
            "watch file path",
            lambda: files.watch_dir(invalid_file_path, lambda event: None),
            status_code=400,
            service="runtime",
            retryable=False,
            message_includes="not a directory",
        )

        path = f"{base_dir}/presign/file.txt"
        upload = await files.upload_url(path, one_time=True)
        assert upload.path == path
        assert upload.method == "PUT"
        upload_response = await asyncio.to_thread(
            fetch_signed_url,
            upload.url,
            method=upload.method,
            body="presigned upload body",
        )
        assert upload_response.status_code == 200
        assert await files.read_text(path) == "presigned upload body"

        download = await files.download_url(path, one_time=True)
        assert download.path == path
        assert download.method == "GET"
        download_response = await asyncio.to_thread(
            fetch_signed_url,
            download.url,
            method=download.method,
        )
        assert download_response.status_code == 200
        assert download_response.text == "presigned upload body"

        path = f"{base_dir}/presign-race/upload.txt"
        upload = await files.upload_url(path, one_time=True)
        first, second = await asyncio.gather(
            asyncio.to_thread(
                fetch_signed_url,
                upload.url,
                method=upload.method,
                body="first body",
            ),
            asyncio.to_thread(
                fetch_signed_url,
                upload.url,
                method=upload.method,
                body="second body",
            ),
        )
        assert sorted([first.status_code, second.status_code]) == [200, 401]
        assert await files.read_text(path) in {"first body", "second body"}

        path = f"{base_dir}/presign-race/download.txt"
        await files.write_text(path, "download once")
        download = await files.download_url(path, one_time=True)
        first, second = await asyncio.gather(
            asyncio.to_thread(fetch_signed_url, download.url, method=download.method),
            asyncio.to_thread(fetch_signed_url, download.url, method=download.method),
        )
        assert sorted([first.status_code, second.status_code]) == [200, 401]
        assert "download once" in {first.text, second.text}

        source = f"{base_dir}/rename-race/source.txt"
        left = f"{base_dir}/rename-race/left.txt"
        right = f"{base_dir}/rename-race/right.txt"
        await files.write_text(source, "race")
        results = await asyncio.gather(
            files.rename(source, left),
            files.rename(source, right),
            return_exceptions=True,
        )
        fulfilled = [result for result in results if not isinstance(result, Exception)]
        rejected = [result for result in results if isinstance(result, Exception)]
        assert len(fulfilled) == 1
        assert len(rejected) == 1
        await expect_hyperbrowser_error_async(
            "rename race failure",
            lambda: _async_raise(rejected[0]),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )
        winner_path = left if await files.exists(left) else right
        assert await files.read_text(winner_path) == "race"

        await expect_hyperbrowser_error_async(
            "missing file read",
            lambda: files.read_text(f"{base_dir}/still-missing.txt"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )

        try:
            await files.list(base_dir, depth=0)
        except ValueError as error:
            assert "depth should be at least one" in str(error)
        else:
            raise AssertionError("expected invalid depth to fail locally")
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await client.close()


async def _async_raise(error):
    raise error
