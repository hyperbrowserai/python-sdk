import time
from typing import Dict, Optional, Union

from ..._request import coerce_request, dump_request
from ....exceptions import HyperbrowserError
from ....models.sandbox import (
    CompleteSandboxImageBuildParams,
    CreateSandboxParams,
    CreateSandboxImageBuildParams,
    SandboxDetail,
    SandboxExecParams,
    SandboxExposeParams,
    SandboxExposeResult,
    SandboxImageBuild,
    SandboxImageBuildCreateResult,
    SandboxImageListParams,
    SandboxImageListResponse,
    SandboxImageInit,
    SandboxListParams,
    SandboxListResponse,
    SandboxMemorySnapshotParams,
    SandboxMemorySnapshotResult,
    SandboxNetworkPolicy,
    SandboxNetworkUpdateResult,
    SandboxRuntimeSession,
    SandboxSnapshotListParams,
    SandboxSnapshotListResponse,
    SandboxUnexposeResult,
    StartSandboxFromSnapshotParams,
)
from ....models.session import BasicResponse
from ....types import (
    CompleteSandboxImageBuildParams as CompleteSandboxImageBuildParamsDict,
    CreateSandboxImageBuildParams as CreateSandboxImageBuildParamsDict,
    CreateSandboxParams as CreateSandboxParamsDict,
    SandboxExecParams as SandboxExecParamsDict,
    SandboxExposeParams as SandboxExposeParamsDict,
    SandboxImageInit as SandboxImageInitDict,
    SandboxImageListParams as SandboxImageListParamsDict,
    SandboxListParams as SandboxListParamsDict,
    SandboxMemorySnapshotParams as SandboxMemorySnapshotParamsDict,
    SandboxNetworkPolicy as SandboxNetworkPolicyDict,
    SandboxSnapshotListParams as SandboxSnapshotListParamsDict,
    StartSandboxFromSnapshotParams as StartSandboxFromSnapshotParamsDict,
)
from ....sandbox_common import (
    RuntimeConnection,
    ensure_response_ok,
    normalize_network_error,
    parse_json_response,
)
from ..sandboxes.shared import (
    _build_sandbox_exposed_url,
    _copy_model,
    _expires_within_buffer,
)
from ..sandboxes.image_build import (
    IMAGE_BUILD_SOURCE_PLATFORM,
    build_docker_image_from_dockerfile,
    is_terminal_image_build_status,
    make_temp_docker_tag,
    package_docker_image,
    remove_docker_image,
    upload_image_build_artifact,
)
from .sandboxes.sandbox_files import (
    DEFAULT_WATCH_TIMEOUT_MS,
    SandboxFileWatchHandle,
    SandboxFilesApi,
    SandboxWatchDirHandle,
)
from .sandboxes.sandbox_processes import (
    DEFAULT_PROCESS_KILL_WAIT_SECONDS,
    SandboxProcessHandle,
    SandboxProcessesApi,
)
from .sandboxes.sandbox_terminal import (
    DEFAULT_TERMINAL_KILL_WAIT_SECONDS,
    SandboxTerminalApi,
    SandboxTerminalConnection,
    SandboxTerminalHandle,
)
from .sandboxes.sandbox_transport import RuntimeTransport

__all__ = [
    "DEFAULT_PROCESS_KILL_WAIT_SECONDS",
    "DEFAULT_TERMINAL_KILL_WAIT_SECONDS",
    "DEFAULT_WATCH_TIMEOUT_MS",
    "RuntimeTransport",
    "SandboxFileWatchHandle",
    "SandboxFilesApi",
    "SandboxHandle",
    "SandboxManager",
    "SandboxProcessHandle",
    "SandboxProcessesApi",
    "SandboxTerminalApi",
    "SandboxTerminalConnection",
    "SandboxTerminalHandle",
    "SandboxWatchDirHandle",
]


class SandboxHandle:
    def __init__(self, service: "SandboxManager", detail: SandboxDetail):
        self._service = service
        self._detail = detail
        self._runtime_session = self._to_runtime_session(detail)
        self._transport = RuntimeTransport(
            self._resolve_runtime_connection,
            service.runtime_timeout,
            service.runtime_proxy_override,
        )
        self.processes = SandboxProcessesApi(self._transport)
        self.files = SandboxFilesApi(
            self._transport,
            self._resolve_runtime_socket_info,
            service.runtime_proxy_override,
        )
        self.terminal = SandboxTerminalApi(
            self._transport,
            self._resolve_runtime_socket_info,
            service.runtime_proxy_override,
        )
        self.pty = self.terminal

    @property
    def id(self) -> str:
        return self._detail.id

    @property
    def status(self) -> str:
        return self._detail.status

    @property
    def region(self):
        return self._detail.region

    @property
    def runtime(self):
        return self._detail.runtime

    @property
    def token_expires_at(self):
        return self._detail.token_expires_at

    @property
    def session_url(self) -> str:
        return self._detail.session_url

    @property
    def cpu(self):
        return self._detail.cpu

    @property
    def memory_mib(self):
        return self._detail.memory_mib

    @property
    def disk_mib(self):
        return self._detail.disk_mib

    @property
    def exposed_ports(self):
        return self._detail.exposed_ports

    @property
    def network(self):
        return self._detail.network

    def to_dict(self):
        return self._detail.model_dump()

    def to_json(self):
        return self.to_dict()

    def info(self) -> SandboxDetail:
        detail = self._service.get_detail(self.id)
        self._hydrate(detail)
        return _copy_model(self._detail)

    def refresh(self) -> "SandboxHandle":
        self.info()
        return self

    def connect(self) -> "SandboxHandle":
        self.create_runtime_session(force_refresh=True)
        return self

    def stop(self) -> BasicResponse:
        response = self._service.stop(self.id)
        self._clear_runtime_session("closed")
        return response

    def create_memory_snapshot(
        self,
        params: Optional[
            Union[SandboxMemorySnapshotParamsDict, SandboxMemorySnapshotParams]
        ] = None,
    ) -> SandboxMemorySnapshotResult:
        return self._service.create_memory_snapshot(
            self.id,
            params if params is not None else {},
        )

    def update_network(
        self,
        policy: Union[SandboxNetworkPolicyDict, SandboxNetworkPolicy],
    ) -> SandboxNetworkUpdateResult:
        result = self._service.update_network(self.id, policy)
        self._detail = self._detail.model_copy(update={"network": result.network})
        return result

    def clear_network(self) -> SandboxNetworkUpdateResult:
        return self.update_network(
            SandboxNetworkPolicy(
                allow_internet_access=True,
                allow_out=[],
                deny_out=[],
            )
        )

    def expose(
        self,
        params: Union[SandboxExposeParamsDict, SandboxExposeParams],
    ) -> SandboxExposeResult:
        result = self._service.expose(self.id, params, runtime=self.runtime)
        exposed_ports = [
            port for port in self._detail.exposed_ports if port.port != result.port
        ]
        exposed_ports.append(result)
        exposed_ports.sort(key=lambda port: port.port)
        self._detail = self._detail.model_copy(update={"exposed_ports": exposed_ports})
        return result

    def unexpose(self, port: int) -> SandboxUnexposeResult:
        result = self._service.unexpose(self.id, port)
        self._detail = self._detail.model_copy(
            update={
                "exposed_ports": [
                    exposed_port
                    for exposed_port in self._detail.exposed_ports
                    if exposed_port.port != port
                ]
            }
        )
        return result

    def get_exposed_url(self, port: int) -> str:
        return _build_sandbox_exposed_url(self.runtime, port)

    def create_runtime_session(
        self, force_refresh: bool = False
    ) -> SandboxRuntimeSession:
        self._assert_runtime_available()
        if (
            not force_refresh
            and self._runtime_session is not None
            and not _expires_within_buffer(self._runtime_session.token_expires_at)
        ):
            return _copy_model(self._runtime_session)

        detail = self._service.get_detail(self.id)
        self._hydrate(detail)
        if self._runtime_session is None:
            raise HyperbrowserError(
                f"Sandbox {self.id} is not running",
                status_code=409,
                code="sandbox_not_running",
                retryable=False,
                service="runtime",
            )
        return _copy_model(self._runtime_session)

    def exec(
        self,
        input: Union[SandboxExecParamsDict, SandboxExecParams, str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        run_as: Optional[str] = None,
    ):
        return self.processes.exec(
            input,
            cwd=cwd,
            env=env,
            timeout_ms=timeout_ms,
            timeout_sec=timeout_sec,
            run_as=run_as,
        )

    def get_process(self, process_id: str) -> SandboxProcessHandle:
        return self.processes.get(process_id)

    def _hydrate(self, detail: SandboxDetail) -> None:
        self._detail = detail
        self._runtime_session = self._to_runtime_session(detail)

    def _resolve_runtime_connection(
        self, force_refresh: bool = False
    ) -> RuntimeConnection:
        session = self.create_runtime_session(force_refresh=force_refresh)
        return RuntimeConnection(
            sandbox_id=self.id,
            base_url=session.runtime.base_url,
            token=session.token,
        )

    def _resolve_runtime_socket_info(self) -> RuntimeConnection:
        session = self.create_runtime_session()
        return RuntimeConnection(
            sandbox_id=self.id,
            base_url=session.runtime.base_url,
            token=session.token,
        )

    def _apply_runtime_session(self, session: SandboxRuntimeSession) -> None:
        self._runtime_session = _copy_model(session)
        self._detail = self._detail.model_copy(
            update={
                "status": session.status,
                "region": session.region,
                "runtime": session.runtime,
                "token": session.token,
                "token_expires_at": session.token_expires_at,
            }
        )

    def _clear_runtime_session(self, status: Optional[str] = None) -> None:
        self._runtime_session = None
        self._detail = self._detail.model_copy(
            update={
                "status": status or self._detail.status,
                "token": None,
                "token_expires_at": None,
            }
        )

    def _assert_runtime_available(self) -> None:
        if self._detail.status in {"closed", "error"}:
            raise HyperbrowserError(
                f"Sandbox {self.id} is not running",
                status_code=409,
                code="sandbox_not_running",
                retryable=False,
                service="runtime",
            )

    @staticmethod
    def _to_runtime_session(detail: SandboxDetail) -> Optional[SandboxRuntimeSession]:
        if not detail.token:
            return None
        return SandboxRuntimeSession(
            sandbox_id=detail.id,
            status=detail.status,
            region=detail.region,
            token=detail.token,
            token_expires_at=detail.token_expires_at,
            runtime=detail.runtime,
        )


class SandboxManager:
    def __init__(self, client):
        self._client = client
        self.runtime_timeout = getattr(client, "timeout", 30)
        self.runtime_proxy_override = getattr(
            client.config,
            "runtime_proxy_override",
            None,
        )

    def create(
        self,
        params: Union[CreateSandboxParamsDict, CreateSandboxParams],
    ) -> SandboxHandle:
        detail = self._create_detail(params)
        return self.attach(detail)

    def start_from_snapshot(
        self,
        params: Union[
            StartSandboxFromSnapshotParamsDict,
            StartSandboxFromSnapshotParams,
        ],
    ) -> SandboxHandle:
        normalized = coerce_request(params, StartSandboxFromSnapshotParams)
        return self.create(normalized)

    def get(self, sandbox_id: str) -> SandboxHandle:
        return self.attach(self.get_detail(sandbox_id))

    def connect(self, sandbox_id: str) -> SandboxHandle:
        sandbox = self.get(sandbox_id)
        sandbox.connect()
        return sandbox

    def list(
        self,
        params: Optional[Union[SandboxListParamsDict, SandboxListParams]] = None,
    ) -> SandboxListResponse:
        payload = self._request(
            "GET",
            "/sandboxes",
            params=dump_request(
                params if params is not None else {},
                SandboxListParams,
            ),
        )
        return SandboxListResponse(**payload)

    def list_images(
        self,
        params: Optional[
            Union[SandboxImageListParamsDict, SandboxImageListParams]
        ] = None,
    ) -> SandboxImageListResponse:
        payload = self._request(
            "GET",
            "/images",
            params=dump_request(
                params if params is not None else {},
                SandboxImageListParams,
            ),
        )
        return SandboxImageListResponse(**payload)

    def list_snapshots(
        self,
        params: Optional[
            Union[SandboxSnapshotListParamsDict, SandboxSnapshotListParams]
        ] = None,
    ) -> SandboxSnapshotListResponse:
        payload = self._request(
            "GET",
            "/snapshots",
            params=dump_request(
                params if params is not None else {},
                SandboxSnapshotListParams,
            ),
        )
        return SandboxSnapshotListResponse(**payload)

    def stop(self, sandbox_id: str) -> BasicResponse:
        payload = self._request("PUT", f"/sandbox/{sandbox_id}/stop")
        return BasicResponse(**payload)

    def create_image_build(
        self,
        params: Union[
            CreateSandboxImageBuildParamsDict,
            CreateSandboxImageBuildParams,
        ],
    ) -> SandboxImageBuildCreateResult:
        payload = self._request(
            "POST",
            "/images/builds",
            data=dump_request(params, CreateSandboxImageBuildParams),
        )
        return SandboxImageBuildCreateResult(**payload)

    def get_image_build(self, build_id: str) -> SandboxImageBuild:
        payload = self._request("GET", f"/images/builds/{build_id}")
        return SandboxImageBuild(**payload["build"])

    def complete_image_build(
        self,
        build_id: str,
        params: Union[
            CompleteSandboxImageBuildParamsDict,
            CompleteSandboxImageBuildParams,
        ],
    ) -> SandboxImageBuild:
        payload = self._request(
            "POST",
            f"/images/builds/{build_id}/complete",
            data=dump_request(params, CompleteSandboxImageBuildParams),
        )
        return SandboxImageBuild(**payload["build"])

    def cancel_image_build(self, build_id: str) -> SandboxImageBuild:
        payload = self._request("POST", f"/images/builds/{build_id}/cancel")
        return SandboxImageBuild(**payload["build"])

    def wait_for_image_build(
        self,
        build_id: str,
        *,
        poll_interval: float = 3.0,
        timeout: Optional[float] = 35 * 60,
    ) -> SandboxImageBuild:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            build = self.get_image_build(build_id)
            if build.status == "completed":
                return build
            if build.status == "failed":
                message = build.error_message or "image build failed"
                if build.error_code:
                    message = f"image build failed [{build.error_code}]: {message}"
                raise RuntimeError(message)
            if is_terminal_image_build_status(build.status):
                raise RuntimeError(f"image build {build.status}")
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for image build {build_id}")
            time.sleep(poll_interval)

    def build_image_from_docker_image(
        self,
        *,
        docker_image: str,
        image_name: str,
        platform: str = IMAGE_BUILD_SOURCE_PLATFORM,
        image_init: Optional[Union[SandboxImageInitDict, SandboxImageInit]] = None,
        image_config_user: Optional[str] = None,
        wait: bool = True,
        poll_interval: float = 3.0,
        wait_timeout: Optional[float] = 35 * 60,
        temp_dir: Optional[str] = None,
        upload_timeout: Optional[float] = None,
    ) -> SandboxImageBuild:
        artifact = package_docker_image(
            docker_image,
            platform=platform,
            temp_dir=temp_dir,
        )
        try:
            normalized_image_init = (
                coerce_request(image_init, SandboxImageInit, name="image_init")
                if image_init is not None
                else artifact.image_init
            )
            create_result = self.create_image_build(
                CreateSandboxImageBuildParams(
                    image_name=image_name,
                    input_sha256=artifact.sha256_hex,
                    input_size_bytes=artifact.size_bytes,
                    input_format=artifact.input_format,
                    source_platform=artifact.source_platform,
                    image_config_user=(
                        image_config_user
                        if image_config_user is not None
                        else artifact.image_config_user
                    ),
                    image_init=normalized_image_init,
                )
            )
            upload_image_build_artifact(
                create_result.upload,
                artifact.path,
                timeout=upload_timeout,
            )
            build = self.complete_image_build(
                create_result.build.id,
                CompleteSandboxImageBuildParams(
                    input_sha256=artifact.sha256_hex,
                    input_size_bytes=artifact.size_bytes,
                    input_format=artifact.input_format,
                ),
            )
            if wait:
                return self.wait_for_image_build(
                    build.id,
                    poll_interval=poll_interval,
                    timeout=wait_timeout,
                )
            return build
        finally:
            artifact.cleanup()

    def build_image_from_dockerfile(
        self,
        *,
        context_path,
        image_name: str,
        dockerfile="Dockerfile",
        docker_tag: Optional[str] = None,
        platform: str = IMAGE_BUILD_SOURCE_PLATFORM,
        build_args: Optional[Dict[str, str]] = None,
        image_init: Optional[Union[SandboxImageInitDict, SandboxImageInit]] = None,
        image_config_user: Optional[str] = None,
        wait: bool = True,
        poll_interval: float = 3.0,
        wait_timeout: Optional[float] = 35 * 60,
        temp_dir: Optional[str] = None,
        upload_timeout: Optional[float] = None,
    ) -> SandboxImageBuild:
        tag = docker_tag or make_temp_docker_tag()
        remove_tag = docker_tag is None
        try:
            build_docker_image_from_dockerfile(
                context_path=context_path,
                dockerfile=dockerfile,
                tag=tag,
                platform=platform,
                build_args=build_args,
            )
            return self.build_image_from_docker_image(
                docker_image=tag,
                image_name=image_name,
                platform=platform,
                image_init=image_init,
                image_config_user=image_config_user,
                wait=wait,
                poll_interval=poll_interval,
                wait_timeout=wait_timeout,
                temp_dir=temp_dir,
                upload_timeout=upload_timeout,
            )
        finally:
            if remove_tag:
                remove_docker_image(tag)

    def get_runtime_session(self, sandbox_id: str) -> SandboxRuntimeSession:
        detail = self.get_detail(sandbox_id)
        session = SandboxHandle._to_runtime_session(detail)
        if session is None:
            raise HyperbrowserError(
                f"Sandbox {sandbox_id} is not running",
                status_code=409,
                code="sandbox_not_running",
                retryable=False,
                service="runtime",
            )
        return session

    def get_detail(self, sandbox_id: str) -> SandboxDetail:
        payload = self._request("GET", f"/sandbox/{sandbox_id}")
        return SandboxDetail(**payload)

    def attach(self, detail: SandboxDetail) -> SandboxHandle:
        return SandboxHandle(self, detail)

    def create_memory_snapshot(
        self,
        sandbox_id: str,
        params: Optional[
            Union[SandboxMemorySnapshotParamsDict, SandboxMemorySnapshotParams]
        ] = None,
    ) -> SandboxMemorySnapshotResult:
        payload = self._request(
            "POST",
            f"/sandbox/{sandbox_id}/snapshot",
            data=dump_request(
                params if params is not None else {},
                SandboxMemorySnapshotParams,
            ),
        )
        return SandboxMemorySnapshotResult(**payload)

    def update_network(
        self,
        sandbox_id: str,
        policy: Union[SandboxNetworkPolicyDict, SandboxNetworkPolicy],
    ) -> SandboxNetworkUpdateResult:
        payload = self._request(
            "PUT",
            f"/sandbox/{sandbox_id}/network",
            data=dump_request(
                policy,
                SandboxNetworkPolicy,
                exclude_unset=True,
                name="policy",
            ),
        )
        return SandboxNetworkUpdateResult(**payload)

    def expose(
        self,
        sandbox_id: str,
        params: Union[SandboxExposeParamsDict, SandboxExposeParams],
        *,
        runtime=None,
    ) -> SandboxExposeResult:
        payload = self._request(
            "POST",
            f"/sandbox/{sandbox_id}/expose",
            data=dump_request(params, SandboxExposeParams),
        )
        target_runtime = runtime or self.get_detail(sandbox_id).runtime
        if "url" not in payload:
            payload["url"] = _build_sandbox_exposed_url(target_runtime, payload["port"])
        return SandboxExposeResult(**payload)

    def unexpose(self, sandbox_id: str, port: int) -> SandboxUnexposeResult:
        payload = self._request(
            "POST",
            f"/sandbox/{sandbox_id}/unexpose",
            data={"port": port},
        )
        return SandboxUnexposeResult(**payload)

    def _create_detail(
        self,
        params: Union[CreateSandboxParamsDict, CreateSandboxParams],
    ) -> SandboxDetail:
        payload = self._request(
            "POST",
            "/sandbox",
            data=dump_request(params, CreateSandboxParams),
        )
        return SandboxDetail(**payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        data: Optional[Dict[str, object]] = None,
    ):
        try:
            response = self._client.transport.client.request(
                method,
                self._client._build_url(path),
                params={k: v for k, v in (params or {}).items() if v is not None},
                json=data,
            )
        except BaseException as error:
            raise normalize_network_error(
                error,
                "control",
                "Unknown error occurred",
            )

        ensure_response_ok(response, "control")
        return parse_json_response(response, "control")
