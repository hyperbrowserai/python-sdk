from collections.abc import Mapping as MappingABC
from abc import ABC, abstractmethod
from typing import Generic, Mapping, Optional, Type, TypeVar, Union

from hyperbrowser.exceptions import HyperbrowserError

T = TypeVar("T")


class APIResponse(Generic[T]):
    """
    Wrapper for API responses to standardize sync/async handling.
    """

    def __init__(self, data: Optional[Union[dict, T]] = None, status_code: int = 200):
        self.data = data
        self.status_code = status_code

    @classmethod
    def from_json(
        cls, json_data: Mapping[str, object], model: Type[T]
    ) -> "APIResponse[T]":
        """Create an APIResponse from JSON data with a specific model."""
        model_name = getattr(model, "__name__", "response model")
        if not isinstance(json_data, MappingABC):
            actual_type_name = type(json_data).__name__
            raise HyperbrowserError(
                f"Failed to parse response data for {model_name}: "
                f"expected a mapping but received {actual_type_name}"
            )
        try:
            return cls(data=model(**json_data))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse response data for {model_name}",
                original_error=exc,
            ) from exc

    @classmethod
    def from_status(cls, status_code: int) -> "APIResponse[None]":
        """Create an APIResponse from just a status code."""
        return cls(data=None, status_code=status_code)

    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return 200 <= self.status_code < 300


class SyncTransportStrategy(ABC):
    """Abstract base class for synchronous transport implementations"""

    @abstractmethod
    def __init__(self, api_key: str, headers: Optional[Mapping[str, str]] = None): ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def post(
        self, url: str, data: Optional[dict] = None, files: Optional[dict] = None
    ) -> APIResponse: ...

    @abstractmethod
    def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse: ...

    @abstractmethod
    def put(self, url: str, data: Optional[dict] = None) -> APIResponse: ...

    @abstractmethod
    def delete(self, url: str) -> APIResponse: ...


class AsyncTransportStrategy(ABC):
    """Abstract base class for asynchronous transport implementations"""

    @abstractmethod
    def __init__(self, api_key: str, headers: Optional[Mapping[str, str]] = None): ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def post(
        self, url: str, data: Optional[dict] = None, files: Optional[dict] = None
    ) -> APIResponse: ...

    @abstractmethod
    async def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse: ...

    @abstractmethod
    async def put(self, url: str, data: Optional[dict] = None) -> APIResponse: ...

    @abstractmethod
    async def delete(self, url: str) -> APIResponse: ...


class TransportStrategy(SyncTransportStrategy):
    """Backward-compatible alias for the sync transport interface."""
