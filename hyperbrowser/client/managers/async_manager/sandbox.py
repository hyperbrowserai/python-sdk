from typing import Dict, Optional, Union

from ....exceptions import HyperbrowserError
from ....models.sandbox import (
    CreateSandboxParams,
    SandboxDetail,
    SandboxExecParams,
    SandboxExposeParams,
    SandboxExposeResult,
    SandboxImageListResponse,
    SandboxListParams,
    SandboxListResponse,
    SandboxMemorySnapshotParams,
    SandboxMemorySnapshotResult,
    SandboxRuntimeSession,
    SandboxSnapshotListParams,
    SandboxSnapshotListResponse,
    SandboxUnexposeResult,
    StartSandboxFromSnapshotParams,
)
from ....models.session import BasicResponse
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

    def to_dict(self):
        return self._detail.model_dump()

    def to_json(self):
        return self.to_dict()

    async def info(self) -> SandboxDetail:
        detail = await self._service.get_detail(self.id)
        self._hydrate(detail)
        return _copy_model(self._detail)

    async def refresh(self) -> "SandboxHandle":
        await self.info()
        return self

    async def connect(self) -> "SandboxHandle":
        await self.create_runtime_session(force_refresh=True)
        return self

    async def stop(self) -> BasicResponse:
        response = await self._service.stop(self.id)
        self._clear_runtime_session("closed")
        return response

    async def create_memory_snapshot(
        self,
        params: Optional[SandboxMemorySnapshotParams] = None,
    ) -> SandboxMemorySnapshotResult:
        if params is None:
            normalized = SandboxMemorySnapshotParams()
        elif isinstance(params, SandboxMemorySnapshotParams):
            normalized = params
        else:
            raise TypeError("params must be a SandboxMemorySnapshotParams instance")
        return await self._service.create_memory_snapshot(self.id, normalized)

    async def expose(self, params: SandboxExposeParams) -> SandboxExposeResult:
        if not isinstance(params, SandboxExposeParams):
            raise TypeError("params must be a SandboxExposeParams instance")
        result = await self._service.expose(self.id, params, runtime=self.runtime)
        exposed_ports = [
            port for port in self._detail.exposed_ports if port.port != result.port
        ]
        exposed_ports.append(result)
        exposed_ports.sort(key=lambda port: port.port)
        self._detail = self._detail.model_copy(update={"exposed_ports": exposed_ports})
        return result

    async def unexpose(self, port: int) -> SandboxUnexposeResult:
        result = await self._service.unexpose(self.id, port)
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

    async def create_runtime_session(
        self, force_refresh: bool = False
    ) -> SandboxRuntimeSession:
        self._assert_runtime_available()
        if (
            not force_refresh
            and self._runtime_session is not None
            and not _expires_within_buffer(self._runtime_session.token_expires_at)
        ):
            return _copy_model(self._runtime_session)

        detail = await self._service.get_detail(self.id)
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

    async def exec(
        self,
        input: Union[str, SandboxExecParams],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        run_as: Optional[str] = None,
    ):
        return await self.processes.exec(
            input,
            cwd=cwd,
            env=env,
            timeout_ms=timeout_ms,
            timeout_sec=timeout_sec,
            run_as=run_as,
        )

    async def get_process(self, process_id: str) -> SandboxProcessHandle:
        return await self.processes.get(process_id)

    def _hydrate(self, detail: SandboxDetail) -> None:
        self._detail = detail
        self._runtime_session = self._to_runtime_session(detail)

    async def _resolve_runtime_connection(
        self, force_refresh: bool = False
    ) -> RuntimeConnection:
        session = await self.create_runtime_session(force_refresh=force_refresh)
        return RuntimeConnection(
            sandbox_id=self.id,
            base_url=session.runtime.base_url,
            token=session.token,
        )

    async def _resolve_runtime_socket_info(self) -> RuntimeConnection:
        session = await self.create_runtime_session()
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

    async def create(self, params: CreateSandboxParams) -> SandboxHandle:
        if not isinstance(params, CreateSandboxParams):
            raise TypeError("params must be a CreateSandboxParams instance")
        detail = await self._create_detail(params)
        return self.attach(detail)

    async def start_from_snapshot(
        self, params: StartSandboxFromSnapshotParams
    ) -> SandboxHandle:
        if not isinstance(params, StartSandboxFromSnapshotParams):
            raise TypeError("params must be a StartSandboxFromSnapshotParams instance")
        return await self.create(params)

    async def get(self, sandbox_id: str) -> SandboxHandle:
        return self.attach(await self.get_detail(sandbox_id))

    async def connect(self, sandbox_id: str) -> SandboxHandle:
        sandbox = await self.get(sandbox_id)
        await sandbox.connect()
        return sandbox

    async def list(
        self, params: SandboxListParams = SandboxListParams()
    ) -> SandboxListResponse:
        if not isinstance(params, SandboxListParams):
            raise TypeError("params must be a SandboxListParams instance")
        payload = await self._request(
            "GET",
            "/sandboxes",
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SandboxListResponse(**payload)

    async def list_images(self) -> SandboxImageListResponse:
        payload = await self._request("GET", "/images")
        return SandboxImageListResponse(**payload)

    async def list_snapshots(
        self, params: SandboxSnapshotListParams = SandboxSnapshotListParams()
    ) -> SandboxSnapshotListResponse:
        if not isinstance(params, SandboxSnapshotListParams):
            raise TypeError("params must be a SandboxSnapshotListParams instance")
        payload = await self._request(
            "GET",
            "/snapshots",
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SandboxSnapshotListResponse(**payload)

    async def stop(self, sandbox_id: str) -> BasicResponse:
        payload = await self._request("PUT", f"/sandbox/{sandbox_id}/stop")
        return BasicResponse(**payload)

    async def get_runtime_session(self, sandbox_id: str) -> SandboxRuntimeSession:
        detail = await self.get_detail(sandbox_id)
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

    async def get_detail(self, sandbox_id: str) -> SandboxDetail:
        payload = await self._request("GET", f"/sandbox/{sandbox_id}")
        return SandboxDetail(**payload)

    def attach(self, detail: SandboxDetail) -> SandboxHandle:
        return SandboxHandle(self, detail)

    async def create_memory_snapshot(
        self,
        sandbox_id: str,
        params: Optional[SandboxMemorySnapshotParams] = None,
    ) -> SandboxMemorySnapshotResult:
        payload = await self._request(
            "POST",
            f"/sandbox/{sandbox_id}/snapshot",
            data=(params or SandboxMemorySnapshotParams()).model_dump(
                exclude_none=True, by_alias=True
            ),
        )
        return SandboxMemorySnapshotResult(**payload)

    async def expose(
        self,
        sandbox_id: str,
        params: SandboxExposeParams,
        *,
        runtime=None,
    ) -> SandboxExposeResult:
        payload = await self._request(
            "POST",
            f"/sandbox/{sandbox_id}/expose",
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        target_runtime = runtime or (await self.get_detail(sandbox_id)).runtime
        if "url" not in payload:
            payload["url"] = _build_sandbox_exposed_url(target_runtime, payload["port"])
        return SandboxExposeResult(**payload)

    async def unexpose(self, sandbox_id: str, port: int) -> SandboxUnexposeResult:
        payload = await self._request(
            "POST",
            f"/sandbox/{sandbox_id}/unexpose",
            data={"port": port},
        )
        return SandboxUnexposeResult(**payload)

    async def _create_detail(self, params: CreateSandboxParams) -> SandboxDetail:
        payload = await self._request(
            "POST",
            "/sandbox",
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SandboxDetail(**payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        data: Optional[Dict[str, object]] = None,
    ):
        try:
            response = await self._client.transport.client.request(
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
