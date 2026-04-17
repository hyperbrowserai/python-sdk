from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from hyperbrowser.exceptions import HyperbrowserError

if TYPE_CHECKING:
    from hyperbrowser.control_auth import ControlPlaneAuthManager

T = TypeVar("T")
ReplayableContent = Union[str, bytes, bytearray, memoryview]


class APIResponse(Generic[T]):
    """
    Wrapper for API responses to standardize sync/async handling.
    """

    def __init__(self, data: Optional[Union[dict, T]] = None, status_code: int = 200):
        self.data = data
        self.status_code = status_code

    @classmethod
    def from_json(cls, json_data: dict, model: Type[T]) -> "APIResponse[T]":
        """Create an APIResponse from JSON data with a specific model."""
        try:
            return cls(data=model(**json_data))
        except Exception as error:
            raise HyperbrowserError(
                "Failed to parse response data", original_error=error
            )

    @classmethod
    def from_status(cls, status_code: int) -> "APIResponse[None]":
        """Create an APIResponse from just a status code."""
        return cls(data=None, status_code=status_code)

    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return 200 <= self.status_code < 300


@dataclass
class PreparedRequest:
    params: Optional[dict] = None
    headers: Dict[str, str] = field(default_factory=dict)
    json_data: Optional[Any] = None
    data: Optional[Any] = None
    content: Optional[ReplayableContent] = None
    files: Optional[Any] = None
    replayable: bool = True
    closeables: List[Any] = field(default_factory=list)

    def close(self) -> None:
        for closeable in self.closeables:
            try:
                closeable.close()
            except Exception:
                pass


RequestBuilder = Callable[[], PreparedRequest]


class TransportStrategy(ABC):
    """Abstract base class for different transport implementations"""

    @abstractmethod
    def __init__(self, auth: "ControlPlaneAuthManager"):
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def post(
        self,
        url: str,
        data: Optional[dict] = None,
        files: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        request_builder: Optional[RequestBuilder] = None,
    ) -> APIResponse:
        pass

    @abstractmethod
    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        follow_redirects: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        pass

    @abstractmethod
    def put(
        self,
        url: str,
        data: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
        request_builder: Optional[RequestBuilder] = None,
    ) -> APIResponse:
        pass

    @abstractmethod
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        pass


def prepare_request(
    *,
    params: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Any] = None,
    data: Optional[Any] = None,
    content: Optional[ReplayableContent] = None,
    files: Optional[Any] = None,
    replayable: Optional[bool] = None,
    closeables: Optional[List[Any]] = None,
) -> PreparedRequest:
    return PreparedRequest(
        params=params,
        headers=normalize_headers(headers),
        json_data=json_data,
        data=data,
        content=content,
        files=files,
        replayable=(
            replayable
            if replayable is not None
            else _is_request_replayable(content=content, files=files)
        ),
        closeables=list(closeables or []),
    )


def normalize_headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
    if not headers:
        return {}
    return {
        str(key).strip().lower(): str(value)
        for key, value in headers.items()
        if value is not None
    }


def build_error_from_response(response: Any, original_error: Optional[Exception] = None):
    error_data = None
    message = ""

    if getattr(response, "content", None):
        try:
            error_data = response.json()
        except Exception:
            error_data = None

    if isinstance(error_data, dict):
        message = str(error_data.get("message") or error_data.get("error") or "")

    if not message:
        try:
            message = response.text or ""
        except Exception:
            message = ""

    if not message:
        message = f"Request failed with status {response.status_code}"

    return HyperbrowserError(
        message,
        status_code=response.status_code,
        response=response,
        original_error=original_error,
        code=error_data.get("code") if isinstance(error_data, dict) else None,
        request_id=response.headers.get("x-request-id"),
        retryable=response.status_code in {408, 409, 425, 429}
        or response.status_code >= 500,
        service="control",
        details=error_data,
    )


def build_network_error(message: str, error: Exception) -> HyperbrowserError:
    return HyperbrowserError(
        message,
        original_error=error,
        retryable=True,
        service="control",
    )


def _is_request_replayable(
    *, content: Optional[ReplayableContent], files: Optional[Any]
) -> bool:
    if files is not None:
        return _are_files_replayable(files)
    if content is None:
        return True
    return isinstance(content, (str, bytes, bytearray, memoryview))


def _are_files_replayable(files: Any) -> bool:
    values: List[Any]
    if isinstance(files, dict):
        values = list(files.values())
    elif isinstance(files, list):
        values = [value for _, value in files]
    elif isinstance(files, tuple) and len(files) == 2:
        values = [files[1]]
    else:
        values = [files]

    return all(_is_file_value_replayable(value) for value in values)


def _is_file_value_replayable(value: Any) -> bool:
    if isinstance(value, tuple) and len(value) >= 2:
        return _is_file_value_replayable(value[1])
    return isinstance(value, (str, bytes, bytearray, memoryview))
