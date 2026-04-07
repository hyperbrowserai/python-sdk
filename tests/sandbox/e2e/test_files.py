from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue

from hyperbrowser.models import SandboxExecParams, SandboxFileWriteEntry

from tests.helpers.config import create_client, make_test_name
from tests.helpers.errors import expect_hyperbrowser_error
from tests.helpers.http import fetch_signed_url
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()


def _bash_exec(command: str, run_as: str = "root") -> SandboxExecParams:
    return SandboxExecParams(command="bash", args=["-lc", command], run_as=run_as)


def _read_stream_text(stream) -> str:
    return stream.read().decode("utf-8")


def _await_queue_value(queue: Queue, timeout: float = 10.0):
    try:
        return queue.get(timeout=timeout)
    except Empty as error:
        raise AssertionError("timed out waiting for watch event") from error


def _create_parent_symlink_escape_fixture(sandbox, base_dir: str, name: str):
    allowed_dir = f"{base_dir}/{name}"
    outside_dir = f"/var/tmp/{make_test_name(name)}"
    outside_file = f"{outside_dir}/secret.txt"
    link_dir = f"{allowed_dir}/evil"
    escaped_file = f"{link_dir}/secret.txt"
    setup = sandbox.exec(
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


def test_sandbox_files_e2e():
    sandbox = None
    base_dir = f"/tmp/{make_test_name('py-sdk-files')}"

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-files"))
        wait_for_runtime_ready(sandbox)
        files = sandbox.files.with_run_as("root")

        assert files.exists(f"{base_dir}/missing.txt") is False

        path = f"{base_dir}/dirs/root"
        assert files.make_dir(path) is True
        assert files.make_dir(path) is False

        info_path = f"{base_dir}/info/hello.txt"
        files.write_text(info_path, "hello from sdk files")
        info = files.get_info(info_path)
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
        files.make_dir(f"{list_dir}/nested/inner", parents=True)
        files.write_text(f"{list_dir}/root.txt", "root")
        files.write_text(f"{list_dir}/nested/child.txt", "child")
        files.write_text(
            f"{list_dir}/nested/inner/grandchild.txt", "grandchild"
        )

        depth_one = files.list(list_dir, depth=1)
        assert [entry.name for entry in depth_one] == ["nested", "root.txt"]
        assert [entry.type for entry in depth_one] == ["dir", "file"]

        depth_two = files.list(list_dir, depth=2)
        assert [entry.path for entry in depth_two] == [
            f"{list_dir}/nested",
            f"{list_dir}/nested/child.txt",
            f"{list_dir}/nested/inner",
            f"{list_dir}/root.txt",
        ]

        symlink_dir = f"{base_dir}/list-symlink"
        target = f"{symlink_dir}/target.txt"
        link = f"{symlink_dir}/link.txt"
        files.make_dir(symlink_dir)
        files.write_text(target, "payload")
        result = sandbox.exec(_bash_exec(f'ln -sfn "{target}" "{link}"'))
        assert result.exit_code == 0
        link_entry = next(
            entry
            for entry in files.list(symlink_dir, depth=1)
            if entry.path == link
        )
        assert link_entry.symlink_target == target

        symlink_target = f"{base_dir}/symlink/target.txt"
        symlink_link = f"{base_dir}/symlink/link.txt"
        files.write_text(symlink_target, "target")
        result = sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/symlink" && ln -sfn "{symlink_target}" "{symlink_link}"'
            )
        )
        assert result.exit_code == 0
        assert files.get_info(symlink_link).symlink_target == symlink_target

        broken_target = f"{base_dir}/symlink-broken/missing-target.txt"
        broken_link = f"{base_dir}/symlink-broken/link.txt"
        result = sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/symlink-broken" && ln -sfn "{broken_target}" "{broken_link}"'
            )
        )
        assert result.exit_code == 0
        assert files.exists(broken_link) is True
        assert files.get_info(broken_link).symlink_target == broken_target

        read_path = f"{base_dir}/read/readme.txt"
        files.write_text(read_path, "hello from sdk files")
        assert files.read(read_path) == "hello from sdk files"
        assert (
            files.read(read_path, format="text", offset=6, length=4) == "from"
        )
        assert files.read(read_path, format="bytes") == b"hello from sdk files"
        assert files.read(read_path, format="blob") == b"hello from sdk files"
        assert (
            _read_stream_text(files.read(read_path, format="stream"))
            == "hello from sdk files"
        )

        single = files.write(f"{base_dir}/write/single.txt", "single file")
        assert single.name == "single.txt"
        assert single.path == f"{base_dir}/write/single.txt"
        assert files.read_text(single.path) == "single file"

        batch = files.write(
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
        assert files.read_text(f"{base_dir}/write/batch-a.txt") == "batch-a"
        assert files.read_bytes(f"{base_dir}/write/batch-b.bin") == bytes(
            [1, 2, 3, 4]
        )

        text_path = f"{base_dir}/write-options/text.txt"
        files.write_text(text_path, "hello", mode="0640")
        files.write_text(text_path, " world", append=True)
        assert files.read_text(text_path) == "hello world"
        assert files.get_info(text_path).mode == 0o640

        bytes_path = f"{base_dir}/write-options/bytes.bin"
        files.write_bytes(bytes_path, bytes([1, 2]), mode="0600")
        files.write_bytes(bytes_path, bytes([3]), append=True)
        assert files.read_bytes(bytes_path) == bytes([1, 2, 3])

        transfer_path = f"{base_dir}/transfer/upload.txt"
        uploaded = files.upload(transfer_path, "uploaded from sdk")
        assert uploaded.bytes_written > 0
        assert (
            files.download(transfer_path).decode("utf-8") == "uploaded from sdk"
        )

        file_path = f"{base_dir}/rename/hello.txt"
        renamed_path = f"{base_dir}/rename/hello-renamed.txt"
        files.write_text(file_path, "rename me")
        renamed = files.rename(file_path, renamed_path)
        assert renamed.path == renamed_path
        assert files.exists(file_path) is False
        assert files.read_text(renamed_path) == "rename me"

        link_path = f"{base_dir}/rename/hello-link.txt"
        copied_link_path = f"{base_dir}/rename/hello-link-copy.txt"
        renamed_link_path = f"{base_dir}/rename/hello-link-renamed.txt"
        result = sandbox.exec(_bash_exec(f'ln -sfn "{renamed_path}" "{link_path}"'))
        assert result.exit_code == 0
        copied_link = files.copy(source=link_path, destination=copied_link_path)
        assert copied_link.path == copied_link_path
        assert files.get_info(copied_link_path).symlink_target == renamed_path
        renamed_link = files.rename(copied_link_path, renamed_link_path)
        assert renamed_link.path == renamed_link_path
        assert files.get_info(renamed_link_path).symlink_target == renamed_path

        target_dir = f"{base_dir}/rename-dir/target-dir"
        link_dir = f"{base_dir}/rename-dir/link-dir"
        renamed_link_dir = f"{base_dir}/rename-dir/link-dir-renamed"
        files.make_dir(target_dir)
        files.write_text(f"{target_dir}/child.txt", "child")
        result = sandbox.exec(_bash_exec(f'ln -sfn "{target_dir}" "{link_dir}"'))
        assert result.exit_code == 0
        renamed = files.rename(link_dir, renamed_link_dir)
        assert renamed.path == renamed_link_dir
        assert files.get_info(renamed_link_dir).symlink_target == target_dir
        assert [
            entry.path for entry in files.list(renamed_link_dir, depth=1)
        ] == [f"{target_dir}/child.txt"]

        source_dir = f"{base_dir}/copy-tree/source"
        nested_dir = f"{source_dir}/nested"
        nested_target = f"{nested_dir}/target.txt"
        destination_dir = f"{base_dir}/copy-tree/destination"
        files.make_dir(nested_dir)
        files.write_text(nested_target, "payload")
        result = sandbox.exec(
            _bash_exec(f'cd "{nested_dir}" && ln -sfn "target.txt" "link.txt"')
        )
        assert result.exit_code == 0
        files.copy(
            source=source_dir, destination=destination_dir, recursive=True
        )
        copied_target = f"{destination_dir}/nested/target.txt"
        copied_link = f"{destination_dir}/nested/link.txt"
        assert files.read_text(copied_target) == "payload"
        assert files.get_info(copied_link).symlink_target == copied_target

        loop_dir = f"{base_dir}/loop-list"
        loop_nested_dir = f"{loop_dir}/nested"
        files.make_dir(loop_nested_dir)
        files.write_text(f"{loop_nested_dir}/child.txt", "payload")
        result = sandbox.exec(_bash_exec(f'cd "{loop_nested_dir}" && ln -sfn .. loop'))
        assert result.exit_code == 0
        loop_entries = files.list(loop_dir, depth=4)
        loop_paths = [entry.path for entry in loop_entries]
        assert f"{loop_nested_dir}/loop" in loop_paths
        assert not any("/loop/" in path for path in loop_paths)
        assert (
            files.get_info(f"{loop_nested_dir}/loop").symlink_target == loop_dir
        )

        source_dir = f"{base_dir}/loop-copy/source"
        nested_dir = f"{source_dir}/nested"
        files.make_dir(nested_dir)
        files.write_text(f"{nested_dir}/child.txt", "payload")
        result = sandbox.exec(_bash_exec(f'cd "{nested_dir}" && ln -sfn .. loop'))
        assert result.exit_code == 0
        destination_dir = f"{base_dir}/loop-copy/destination"
        files.copy(
            source=source_dir, destination=destination_dir, recursive=True
        )
        copied_loop = f"{destination_dir}/nested/loop"
        assert files.get_info(copied_loop).symlink_target == destination_dir
        assert not any(
            "/loop/" in entry.path
            for entry in files.list(destination_dir, depth=4)
        )

        source = f"{base_dir}/copy-overwrite/source.txt"
        existing_target = f"{base_dir}/copy-overwrite/existing-target.txt"
        destination_link = f"{base_dir}/copy-overwrite/destination-link.txt"
        files.write_text(source, "source payload")
        files.write_text(existing_target, "existing target")
        result = sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/copy-overwrite" && ln -sfn "{existing_target}" "{destination_link}"'
            )
        )
        assert result.exit_code == 0
        files.copy(source=source, destination=destination_link, overwrite=True)
        assert files.read_text(destination_link) == "source payload"
        assert files.read_text(existing_target) == "existing target"
        assert files.get_info(destination_link).symlink_target is None

        move_source = f"{base_dir}/move-overwrite/source.txt"
        move_existing_target = f"{base_dir}/move-overwrite/existing-target.txt"
        move_destination_link = f"{base_dir}/move-overwrite/destination-link.txt"
        files.write_text(move_source, "move source payload")
        files.write_text(move_existing_target, "move existing target")
        result = sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/move-overwrite" && ln -sfn "{move_existing_target}" "{move_destination_link}"'
            )
        )
        assert result.exit_code == 0
        files.move(
            source=move_source,
            destination=move_destination_link,
            overwrite=True,
        )
        assert files.read_text(move_destination_link) == "move source payload"
        assert files.read_text(move_existing_target) == "move existing target"
        assert files.get_info(move_destination_link).symlink_target is None
        assert files.exists(move_source) is False

        chmod_path = f"{base_dir}/chmod/file.txt"
        files.write_text(chmod_path, "chmod me")
        files.chmod(path=chmod_path, mode="0640")
        assert files.get_info(chmod_path).mode == 0o640
        try:
            expect_hyperbrowser_error(
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
            assert files.get_info(chmod_path).name == "file.txt"

        remove_path = f"{base_dir}/remove/file.txt"
        files.write_text(remove_path, "remove me")
        files.remove(remove_path)
        assert files.exists(remove_path) is False
        files.remove(remove_path)
        files.remove(f"{base_dir}/remove", recursive=True)
        assert files.exists(f"{base_dir}/remove") is False

        target = f"{base_dir}/remove-link/target.txt"
        link = f"{base_dir}/remove-link/link.txt"
        files.write_text(target, "keep me")
        result = sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/remove-link" && ln -sfn "{target}" "{link}"'
            )
        )
        assert result.exit_code == 0
        files.remove(link)
        assert files.exists(link) is False
        assert files.read_text(target) == "keep me"

        target_dir = f"{base_dir}/remove-recursive/target-dir"
        target_file = f"{target_dir}/child.txt"
        link_dir = f"{base_dir}/remove-recursive/link-dir"
        files.make_dir(target_dir)
        files.write_text(target_file, "keep tree")
        result = sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/remove-recursive" && ln -sfn "{target_dir}" "{link_dir}"'
            )
        )
        assert result.exit_code == 0
        files.remove(link_dir, recursive=True)
        assert files.exists(link_dir) is False
        assert files.read_text(target_file) == "keep tree"

        link = f"{base_dir}/escape/file-link"
        result = sandbox.exec(
            _bash_exec(f'mkdir -p "{base_dir}/escape" && ln -sfn /etc/hosts "{link}"')
        )
        assert result.exit_code == 0
        text = files.read_text(link)
        assert "localhost" in text
        assert "localhost" in files.download(link).decode("utf-8")

        fixture = _create_parent_symlink_escape_fixture(
            sandbox, base_dir, "parent-escape-read"
        )
        assert files.read_text(fixture["escaped_file"]) == "outside secret"
        assert (
            files.download(fixture["escaped_file"]).decode("utf-8")
            == "outside secret"
        )
        assert [
            entry.path for entry in files.list(fixture["link_dir"], depth=1)
        ] == [f"{fixture['outside_dir']}/secret.txt"]
        seen = Queue(maxsize=1)
        handle = files.watch_dir(
            fixture["link_dir"],
            lambda event: (
                seen.put_nowait(event.name)
                if event.type in {"create", "write"} and event.name == "fresh.txt"
                else None
            ),
        )
        try:
            files.write_text(
                f"{fixture['outside_dir']}/fresh.txt", "watch parent link"
            )
            assert _await_queue_value(seen) == "fresh.txt"
        finally:
            handle.stop()

        fixture = _create_parent_symlink_escape_fixture(
            sandbox, base_dir, "parent-escape-mutate"
        )
        info = files.get_info(fixture["escaped_file"])
        assert info.type == "file"
        assert info.size == len("outside secret")
        copied = files.copy(
            source=fixture["escaped_file"],
            destination=f"{base_dir}/parent-escape-mutate/copied.txt",
        )
        assert copied.path == f"{base_dir}/parent-escape-mutate/copied.txt"
        assert files.read_text(copied.path) == "outside secret"
        renamed = files.rename(
            fixture["escaped_file"],
            f"{base_dir}/parent-escape-mutate/renamed.txt",
        )
        assert renamed.path == f"{base_dir}/parent-escape-mutate/renamed.txt"
        assert files.exists(fixture["outside_file"]) is False
        assert files.read_text(renamed.path) == "outside secret"
        files.write_text(fixture["escaped_file"], "remove me")
        files.remove(fixture["escaped_file"])
        outside_read = sandbox.exec(
            _bash_exec(
                f'if [ -e "{fixture["outside_file"]}" ]; then cat "{fixture["outside_file"]}"; else printf "__MISSING__"; fi'
            )
        )
        assert outside_read.exit_code == 0
        assert outside_read.stdout.strip() == "__MISSING__"

        target_dir = f"/var/tmp/{make_test_name('watch-outside-target')}"
        target_file = f"{target_dir}/child.txt"
        link = f"{base_dir}/escape/dir-link"
        result = sandbox.exec(
            _bash_exec(
                f'mkdir -p "{base_dir}/escape" "{target_dir}" && printf "child" > "{target_file}" && ln -sfn "{target_dir}" "{link}"'
            )
        )
        assert result.exit_code == 0
        assert [entry.path for entry in files.list(link, depth=1)] == [
            target_file
        ]
        seen = Queue(maxsize=1)
        handle = files.watch_dir(
            link,
            lambda event: (
                seen.put_nowait(event.name)
                if event.type in {"create", "write"} and event.name == "file.txt"
                else None
            ),
        )
        try:
            files.write_text(f"{target_dir}/file.txt", "watch through link")
            assert _await_queue_value(seen) == "file.txt"
        finally:
            handle.stop()

        watch_dir = f"{base_dir}/watch"
        files.make_dir(f"{watch_dir}/nested", parents=True)
        direct_event = Queue(maxsize=1)
        recursive_event = Queue(maxsize=1)
        direct_handle = files.watch_dir(
            watch_dir,
            lambda event: (
                direct_event.put_nowait(event.name)
                if event.type in {"create", "write"} and event.name == "direct.txt"
                else None
            ),
        )
        recursive_handle = files.watch_dir(
            watch_dir,
            lambda event: (
                recursive_event.put_nowait(event.name)
                if event.type in {"create", "write"} and event.name == "nested/recursive.txt"
                else None
            ),
            recursive=True,
        )
        try:
            files.write_text(f"{watch_dir}/direct.txt", "watch me")
            files.write_text(
                f"{watch_dir}/nested/recursive.txt", "watch me too"
            )
            assert _await_queue_value(direct_event) == "direct.txt"
            assert _await_queue_value(recursive_event) == "nested/recursive.txt"
        finally:
            direct_handle.stop()
            recursive_handle.stop()

        expect_hyperbrowser_error(
            "watch missing directory",
            lambda: files.watch_dir(
                f"{base_dir}/watch-missing", lambda event: None
            ),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )

        invalid_file_path = f"{base_dir}/watch-invalid/file.txt"
        files.write_text(invalid_file_path, "not a directory")
        expect_hyperbrowser_error(
            "watch file path",
            lambda: files.watch_dir(invalid_file_path, lambda event: None),
            status_code=400,
            service="runtime",
            retryable=False,
            message_includes="not a directory",
        )

        path = f"{base_dir}/presign/file.txt"
        upload = files.upload_url(path, one_time=True)
        assert upload.path == path
        assert upload.method == "PUT"
        upload_response = fetch_signed_url(
            upload.url,
            method=upload.method,
            body="presigned upload body",
        )
        assert upload_response.status_code == 200
        assert files.read_text(path) == "presigned upload body"

        download = files.download_url(path, one_time=True)
        assert download.path == path
        assert download.method == "GET"
        download_response = fetch_signed_url(download.url, method=download.method)
        assert download_response.status_code == 200
        assert download_response.text == "presigned upload body"

        path = f"{base_dir}/presign-race/upload.txt"
        upload = files.upload_url(path, one_time=True)
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                fetch_signed_url,
                upload.url,
                method=upload.method,
                body="first body",
            )
            second_future = executor.submit(
                fetch_signed_url,
                upload.url,
                method=upload.method,
                body="second body",
            )
            first = first_future.result()
            second = second_future.result()
        assert sorted([first.status_code, second.status_code]) == [200, 401]
        assert files.read_text(path) in {"first body", "second body"}

        path = f"{base_dir}/presign-race/download.txt"
        files.write_text(path, "download once")
        download = files.download_url(path, one_time=True)
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                fetch_signed_url, download.url, method=download.method
            )
            second_future = executor.submit(
                fetch_signed_url, download.url, method=download.method
            )
            first = first_future.result()
            second = second_future.result()
        assert sorted([first.status_code, second.status_code]) == [200, 401]
        assert "download once" in {first.text, second.text}

        source = f"{base_dir}/rename-race/source.txt"
        left = f"{base_dir}/rename-race/left.txt"
        right = f"{base_dir}/rename-race/right.txt"
        files.write_text(source, "race")
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(files.rename, source, left),
                executor.submit(files.rename, source, right),
            ]
        results = []
        for future in futures:
            try:
                results.append(("fulfilled", future.result()))
            except Exception as error:  # pragma: no cover - exercised in e2e
                results.append(("rejected", error))
        fulfilled = [result for result in results if result[0] == "fulfilled"]
        rejected = [result for result in results if result[0] == "rejected"]
        assert len(fulfilled) == 1
        assert len(rejected) == 1
        expect_hyperbrowser_error(
            "rename race failure",
            lambda: (_ for _ in ()).throw(rejected[0][1]),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )
        winner_path = left if files.exists(left) else right
        assert files.read_text(winner_path) == "race"

        expect_hyperbrowser_error(
            "missing file read",
            lambda: files.read_text(f"{base_dir}/still-missing.txt"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes_any=["not found", "no such file"],
        )

        try:
            files.list(base_dir, depth=0)
        except ValueError as error:
            assert "depth should be at least one" in str(error)
        else:
            raise AssertionError("expected invalid depth to fail locally")
    finally:
        stop_sandbox_if_running(sandbox)
