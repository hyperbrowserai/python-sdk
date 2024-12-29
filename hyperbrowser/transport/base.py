from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic, Type, Union

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
    def __init__(self, api_key: str):
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def post(self, url: str) -> APIResponse:
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
