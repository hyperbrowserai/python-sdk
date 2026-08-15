from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
)

from hyperbrowser.exceptions import HyperbrowserError

if TYPE_CHECKING:
    from hyperbrowser.control_auth import ControlPlaneAuthManager

T = TypeVar("T")


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
        except Exception as e:
            raise HyperbrowserError("Failed to parse response data", original_error=e)

    @classmethod
    def from_status(cls, status_code: int) -> "APIResponse[None]":
        """Create an APIResponse from just a status code."""
        return cls(data=None, status_code=status_code)

    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return 200 <= self.status_code < 300


class TransportStrategy(ABC):
    """Abstract base class for different transport implementations"""

    @abstractmethod
    def __init__(self, auth: Union[str, "ControlPlaneAuthManager"]):
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def post(
        self,
        url: str,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> APIResponse:
        pass

    @abstractmethod
    def get(self, url: str, params: Optional[dict] = None) -> APIResponse:
        pass

    @abstractmethod
    def put(self, url: str) -> APIResponse:
        pass

    @abstractmethod
    def delete(self, url: str) -> APIResponse:
        pass


def is_request_replayable(files: Optional[Any] = None) -> bool:
    if files is None:
        return True
    return _are_files_replayable(files)


def oauth_unauthorized(auth: Any, response: Any) -> bool:
    return response.status_code == 401 and bool(getattr(auth, "is_oauth", False))


def retry_oauth_unauthorized(
    auth: Any,
    response: Any,
    *,
    access_token: Optional[str],
    replayable: bool,
    authorize: Callable[..., Any],
    send: Callable[[Dict[str, str]], Any],
    close_response: Callable[[Any], None],
):
    if not oauth_unauthorized(auth, response):
        return response

    retry_headers, _ = authorize(
        force_refresh=True,
        rejected_access_token=access_token,
    )
    if not replayable:
        return response

    close_response(response)
    return send(retry_headers)


async def aretry_oauth_unauthorized(
    auth: Any,
    response: Any,
    *,
    access_token: Optional[str],
    replayable: bool,
    authorize: Callable[..., Any],
    send: Callable[[Dict[str, str]], Any],
    close_response: Callable[[Any], None],
):
    if not oauth_unauthorized(auth, response):
        return response

    retry_headers, _ = await authorize(
        force_refresh=True,
        rejected_access_token=access_token,
    )
    if not replayable:
        return response

    await close_response(response)
    return await send(retry_headers)


def _are_files_replayable(files: Any) -> bool:
    if isinstance(files, dict):
        values = list(files.values())
    elif _is_file_pair_sequence(files):
        values = [item[1] for item in files]
    elif isinstance(files, tuple) and len(files) >= 2 and isinstance(files[0], str):
        values = [files[1]]
    elif isinstance(files, (list, tuple)):
        values = list(files)
    else:
        values = [files]
    return all(_is_file_value_replayable(value) for value in values)


def _is_file_pair_sequence(files: Any) -> bool:
    if not isinstance(files, (list, tuple)) or not files:
        return False
    first = files[0]
    return isinstance(first, (list, tuple)) and len(first) >= 2


def _is_file_value_replayable(value: Any) -> bool:
    if isinstance(value, tuple) and len(value) >= 2:
        return _is_file_value_replayable(value[1])
    return isinstance(value, (str, bytes, bytearray, memoryview))
