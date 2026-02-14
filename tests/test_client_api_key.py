import pytest

import hyperbrowser.client.base as client_base_module
from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserError


def test_sync_client_requires_api_key_when_not_in_env(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(
        HyperbrowserError,
        match="API key must be provided via `api_key` or HYPERBROWSER_API_KEY",
    ):
        Hyperbrowser()


def test_async_client_requires_api_key_when_not_in_env(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(
        HyperbrowserError,
        match="API key must be provided via `api_key` or HYPERBROWSER_API_KEY",
    ):
        AsyncHyperbrowser()


def test_sync_client_rejects_blank_env_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "   ")

    with pytest.raises(
        HyperbrowserError,
        match="API key must be provided via `api_key` or HYPERBROWSER_API_KEY",
    ):
        Hyperbrowser()


def test_sync_client_rejects_blank_env_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "   ")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        Hyperbrowser()


def test_async_client_rejects_blank_env_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "   ")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        AsyncHyperbrowser()


def test_sync_client_rejects_non_string_api_key():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        Hyperbrowser(api_key=123)  # type: ignore[arg-type]


def test_async_client_rejects_non_string_api_key():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        AsyncHyperbrowser(api_key=123)  # type: ignore[arg-type]


def test_sync_client_rejects_blank_constructor_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")

    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        Hyperbrowser(api_key="   ")


def test_async_client_rejects_blank_constructor_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")

    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        AsyncHyperbrowser(api_key="\t")


def test_sync_client_rejects_control_character_api_key():
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        Hyperbrowser(api_key="bad\nkey")


def test_async_client_rejects_control_character_api_key():
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        AsyncHyperbrowser(api_key="bad\nkey")


def test_sync_client_rejects_control_character_env_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "bad\nkey")

    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        Hyperbrowser()


def test_async_client_rejects_control_character_env_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "bad\nkey")

    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        AsyncHyperbrowser()


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_wraps_api_key_env_read_runtime_errors(
    client_class, monkeypatch: pytest.MonkeyPatch
):
    original_get = client_base_module.os.environ.get

    def _broken_get(env_name: str, default=None):
        if env_name == "HYPERBROWSER_API_KEY":
            raise RuntimeError("api key env read exploded")
        return original_get(env_name, default)

    monkeypatch.setattr(client_base_module.os.environ, "get", _broken_get)

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read HYPERBROWSER_API_KEY environment variable",
    ) as exc_info:
        client_class()

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_preserves_hyperbrowser_api_key_env_read_errors(
    client_class, monkeypatch: pytest.MonkeyPatch
):
    original_get = client_base_module.os.environ.get

    def _broken_get(env_name: str, default=None):
        if env_name == "HYPERBROWSER_API_KEY":
            raise HyperbrowserError("custom api key env read failure")
        return original_get(env_name, default)

    monkeypatch.setattr(client_base_module.os.environ, "get", _broken_get)

    with pytest.raises(
        HyperbrowserError, match="custom api key env read failure"
    ) as exc_info:
        client_class()

    assert exc_info.value.original_error is None


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_wraps_base_url_env_read_runtime_errors(
    client_class, monkeypatch: pytest.MonkeyPatch
):
    original_get = client_base_module.os.environ.get
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")

    def _broken_get(env_name: str, default=None):
        if env_name == "HYPERBROWSER_BASE_URL":
            raise RuntimeError("base url env read exploded")
        return original_get(env_name, default)

    monkeypatch.setattr(client_base_module.os.environ, "get", _broken_get)

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read HYPERBROWSER_BASE_URL environment variable",
    ) as exc_info:
        client_class()

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_wraps_headers_env_read_runtime_errors(
    client_class, monkeypatch: pytest.MonkeyPatch
):
    original_get = client_base_module.os.environ.get
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")

    def _broken_get(env_name: str, default=None):
        if env_name == "HYPERBROWSER_HEADERS":
            raise RuntimeError("headers env read exploded")
        return original_get(env_name, default)

    monkeypatch.setattr(client_base_module.os.environ, "get", _broken_get)

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read HYPERBROWSER_HEADERS environment variable",
    ) as exc_info:
        client_class()

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_wraps_api_key_strip_runtime_errors(client_class):
    class _BrokenStripApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("api key strip exploded")

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        client_class(api_key=_BrokenStripApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_preserves_hyperbrowser_api_key_strip_errors(client_class):
    class _BrokenStripApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise HyperbrowserError("custom strip failure")

    with pytest.raises(HyperbrowserError, match="custom strip failure") as exc_info:
        client_class(api_key=_BrokenStripApiKey("test-key"))

    assert exc_info.value.original_error is None


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_wraps_non_string_api_key_strip_results(client_class):
    class _NonStringStripResultApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return object()

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        client_class(api_key=_NonStringStripResultApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, TypeError)


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_wraps_api_key_string_subclass_strip_results(client_class):
    class _BrokenLengthApiKey(str):
        class _NormalizedKey(str):
            pass

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedKey("test-key")

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        client_class(api_key=_BrokenLengthApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, TypeError)


@pytest.mark.parametrize("client_class", [Hyperbrowser, AsyncHyperbrowser])
def test_client_rejects_blank_api_key_input(client_class):
    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        client_class(api_key="   ")
