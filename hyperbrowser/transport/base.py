from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, TypeVar, Generic, Type, Union

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


def _are_files_replayable(files: Any) -> bool:
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


def merge_headers(
    *header_groups: Optional[Dict[str, str]],
) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for headers in header_groups:
        if not headers:
            continue
        for key, value in headers.items():
            if value is None:
                continue
            merged[str(key)] = str(value)
    return merged
