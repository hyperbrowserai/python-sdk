from types import MappingProxyType
from urllib.parse import quote

import pytest

import hyperbrowser.config as config_module
from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError


def test_client_config_from_env_raises_hyperbrowser_error_without_api_key(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_API_KEY"):
        ClientConfig.from_env()


def test_client_config_from_env_raises_hyperbrowser_error_for_blank_api_key(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "   ")

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_API_KEY"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_control_character_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "bad\nkey")

    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_wraps_api_key_env_read_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    original_get = config_module.os.environ.get

    def _broken_get(env_name: str, default=None):
        if env_name == "HYPERBROWSER_API_KEY":
            raise RuntimeError("api key env read exploded")
        return original_get(env_name, default)

    monkeypatch.setattr(config_module.os.environ, "get", _broken_get)

    with pytest.raises(
        HyperbrowserError,
        match="api key env read exploded",
    ) as exc_info:
        ClientConfig.from_env()

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_from_env_wraps_base_url_env_read_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    original_get = config_module.os.environ.get
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")

    def _broken_get(env_name: str, default=None):
        if env_name == "HYPERBROWSER_BASE_URL":
            raise RuntimeError("base url env read exploded")
        return original_get(env_name, default)

    monkeypatch.setattr(config_module.os.environ, "get", _broken_get)

    with pytest.raises(
        HyperbrowserError,
        match="base url env read exploded",
    ) as exc_info:
        ClientConfig.from_env()

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_from_env_wraps_headers_env_read_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    original_get = config_module.os.environ.get
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://api.hyperbrowser.ai")

    def _broken_get(env_name: str, default=None):
        if env_name == "HYPERBROWSER_HEADERS":
            raise RuntimeError("headers env read exploded")
        return original_get(env_name, default)

    monkeypatch.setattr(config_module.os.environ, "get", _broken_get)

    with pytest.raises(
        HyperbrowserError,
        match="headers env read exploded",
    ) as exc_info:
        ClientConfig.from_env()

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_from_env_preserves_hyperbrowser_env_read_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _broken_read_env(env_name: str):
        if env_name == "HYPERBROWSER_API_KEY":
            raise HyperbrowserError("custom env read failure")
        return None

    monkeypatch.setattr(
        ClientConfig, "_read_env_value", staticmethod(_broken_read_env)
    )

    with pytest.raises(HyperbrowserError, match="custom env read failure") as exc_info:
        ClientConfig.from_env()

    assert exc_info.value.original_error is None


def test_client_config_from_env_reads_api_key_and_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://example.local")

    config = ClientConfig.from_env()

    assert config.api_key == "test-key"
    assert config.base_url == "https://example.local"


def test_client_config_from_env_reads_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Request-Id":"abc123"}')

    config = ClientConfig.from_env()

    assert config.headers == {"X-Request-Id": "abc123"}


def test_client_config_from_env_rejects_invalid_headers_json(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_HEADERS must be valid JSON object"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_non_object_headers_json(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '["not-an-object"]')

    with pytest.raises(
        HyperbrowserError,
        match="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_non_string_header_values(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Request-Id":123}')

    with pytest.raises(
        HyperbrowserError,
        match="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_empty_header_name(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"   ":"value"}')

    with pytest.raises(HyperbrowserError, match="header names must not be empty"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_newline_header_values(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Correlation-Id":"bad\\nvalue"}')

    with pytest.raises(
        HyperbrowserError, match="headers must not contain newline characters"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_duplicate_header_names_after_normalization(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv(
        "HYPERBROWSER_HEADERS",
        '{"X-Correlation-Id":"one","  X-Correlation-Id  ":"two"}',
    )

    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_case_insensitive_duplicate_header_names(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv(
        "HYPERBROWSER_HEADERS",
        '{"X-Correlation-Id":"one","x-correlation-id":"two"}',
    )

    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_ignores_blank_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "   ")

    config = ClientConfig.from_env()

    assert config.headers is None


def test_client_config_from_env_normalizes_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", " https://example.local/ ")

    config = ClientConfig.from_env()

    assert config.base_url == "https://example.local"


def test_client_config_from_env_rejects_invalid_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "example.local")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_blank_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "   ")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_base_url_without_host(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://")

    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_base_url_query_or_fragment(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://example.local?x=1")

    with pytest.raises(HyperbrowserError, match="must not include query parameters"):
        ClientConfig.from_env()


def test_client_config_normalizes_whitespace_and_trailing_slash():
    config = ClientConfig(api_key="  test-key  ", base_url=" https://example.local/ ")

    assert config.api_key == "test-key"
    assert config.base_url == "https://example.local"


def test_client_config_rejects_non_string_values():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        ClientConfig(api_key=None)  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="base_url must be a string"):
        ClientConfig(api_key="test-key", base_url=None)  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="headers must be a mapping"):
        ClientConfig(api_key="test-key", headers="x=1")  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        ClientConfig(api_key="   ")
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        ClientConfig(api_key="bad\nkey")


def test_client_config_normalize_base_url_wraps_strip_runtime_errors():
    class _BrokenBaseUrl(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("base_url strip exploded")

    with pytest.raises(HyperbrowserError, match="Failed to normalize base_url") as exc_info:
        ClientConfig.normalize_base_url(_BrokenBaseUrl("https://example.local"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_normalize_base_url_preserves_hyperbrowser_strip_errors():
    class _BrokenBaseUrl(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise HyperbrowserError("custom base_url strip failure")

    with pytest.raises(
        HyperbrowserError, match="custom base_url strip failure"
    ) as exc_info:
        ClientConfig.normalize_base_url(_BrokenBaseUrl("https://example.local"))

    assert exc_info.value.original_error is None


def test_client_config_normalize_base_url_wraps_non_string_strip_results():
    class _BrokenBaseUrl(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return object()

    with pytest.raises(HyperbrowserError, match="Failed to normalize base_url") as exc_info:
        ClientConfig.normalize_base_url(_BrokenBaseUrl("https://example.local"))

    assert isinstance(exc_info.value.original_error, TypeError)


def test_client_config_resolve_base_url_from_env_wraps_strip_runtime_errors():
    class _BrokenBaseUrl(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("environment base_url strip exploded")

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize HYPERBROWSER_BASE_URL"
    ) as exc_info:
        ClientConfig.resolve_base_url_from_env(_BrokenBaseUrl("https://example.local"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_wraps_api_key_strip_runtime_errors():
    class _BrokenApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("api key strip exploded")

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        ClientConfig(api_key=_BrokenApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_preserves_hyperbrowser_api_key_strip_errors():
    class _BrokenApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise HyperbrowserError("custom strip failure")

    with pytest.raises(HyperbrowserError, match="custom strip failure") as exc_info:
        ClientConfig(api_key=_BrokenApiKey("test-key"))

    assert exc_info.value.original_error is None


def test_client_config_wraps_non_string_api_key_strip_results():
    class _BrokenApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return object()

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        ClientConfig(api_key=_BrokenApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, TypeError)


def test_client_config_wraps_api_key_empty_check_length_failures():
    class _BrokenApiKey(str):
        class _NormalizedKey(str):
            def __len__(self):
                raise RuntimeError("api key length exploded")

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedKey("test-key")

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        ClientConfig(api_key=_BrokenApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_preserves_hyperbrowser_api_key_empty_check_length_failures():
    class _BrokenApiKey(str):
        class _NormalizedKey(str):
            def __len__(self):
                raise HyperbrowserError("custom length failure")

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedKey("test-key")

    with pytest.raises(HyperbrowserError, match="custom length failure") as exc_info:
        ClientConfig(api_key=_BrokenApiKey("test-key"))

    assert exc_info.value.original_error is None


def test_client_config_wraps_api_key_iteration_runtime_errors():
    class _BrokenApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __iter__(self):
            raise RuntimeError("api key iteration exploded")

    with pytest.raises(
        HyperbrowserError, match="Failed to validate api_key characters"
    ) as exc_info:
        ClientConfig(api_key=_BrokenApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_client_config_preserves_hyperbrowser_api_key_iteration_errors():
    class _BrokenApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __iter__(self):
            raise HyperbrowserError("custom iteration failure")

    with pytest.raises(HyperbrowserError, match="custom iteration failure") as exc_info:
        ClientConfig(api_key=_BrokenApiKey("test-key"))

    assert exc_info.value.original_error is None


def test_client_config_rejects_empty_or_invalid_base_url():
    with pytest.raises(HyperbrowserError, match="base_url must not be empty"):
        ClientConfig(api_key="test-key", base_url="   ")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig(api_key="test-key", base_url="api.hyperbrowser.ai")

    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig(api_key="test-key", base_url="http://")
    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig(api_key="test-key", base_url="https://:443")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local:99999")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local:bad")

    with pytest.raises(HyperbrowserError, match="must not include query parameters"):
        ClientConfig(api_key="test-key", base_url="https://example.local#frag")
    with pytest.raises(
        HyperbrowserError, match="base_url must not include user credentials"
    ):
        ClientConfig(api_key="test-key", base_url="https://user:pass@example.local")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain newline characters"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local/\napi")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain whitespace characters"
    ):
        ClientConfig(api_key="test-key", base_url="https://example .local")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain backslashes"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local\\api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain control characters"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local\x00api")
    with pytest.raises(
        HyperbrowserError, match="base_url path must not contain relative path segments"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local/%2e%2e/api")
    with pytest.raises(
        HyperbrowserError,
        match="base_url path must not contain encoded query or fragment delimiters",
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local/%3Fapi")


def test_client_config_normalizes_headers_to_internal_copy():
    headers = {"X-Correlation-Id": "abc123"}
    config = ClientConfig(api_key="test-key", headers=headers)

    headers["X-Correlation-Id"] = "changed"

    assert config.headers == {"X-Correlation-Id": "abc123"}


def test_client_config_rejects_non_string_header_pairs():
    with pytest.raises(HyperbrowserError, match="headers must be a mapping"):
        ClientConfig(api_key="test-key", headers={"X-Correlation-Id": 123})  # type: ignore[dict-item]


def test_client_config_rejects_empty_header_name():
    with pytest.raises(HyperbrowserError, match="header names must not be empty"):
        ClientConfig(api_key="test-key", headers={"   ": "value"})


def test_client_config_rejects_invalid_header_name_characters():
    with pytest.raises(
        HyperbrowserError,
        match="header names must contain only valid HTTP token characters",
    ):
        ClientConfig(api_key="test-key", headers={"X Trace": "value"})


def test_client_config_rejects_overly_long_header_names():
    long_header_name = "X-" + ("a" * 255)

    with pytest.raises(
        HyperbrowserError, match="header names must be 256 characters or fewer"
    ):
        ClientConfig(api_key="test-key", headers={long_header_name: "value"})


def test_client_config_rejects_newline_header_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain newline characters"
    ):
        ClientConfig(api_key="test-key", headers={"X-Correlation-Id": "bad\nvalue"})


def test_client_config_rejects_control_character_header_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain control characters"
    ):
        ClientConfig(api_key="test-key", headers={"X-Correlation-Id": "bad\tvalue"})


def test_client_config_normalizes_header_name_whitespace():
    config = ClientConfig(api_key="test-key", headers={"  X-Correlation-Id  ": "value"})

    assert config.headers == {"X-Correlation-Id": "value"}


def test_client_config_rejects_duplicate_header_names_after_normalization():
    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig(
            api_key="test-key",
            headers={"X-Correlation-Id": "one", "  X-Correlation-Id  ": "two"},
        )


def test_client_config_rejects_case_insensitive_duplicate_header_names():
    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig(
            api_key="test-key",
            headers={"X-Correlation-Id": "one", "x-correlation-id": "two"},
        )


def test_client_config_accepts_mapping_header_inputs():
    headers = MappingProxyType({"X-Correlation-Id": "abc123"})
    config = ClientConfig(api_key="test-key", headers=headers)

    assert config.headers == {"X-Correlation-Id": "abc123"}


def test_client_config_parse_headers_from_env_rejects_non_string_input():
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_HEADERS must be a string"
    ):
        ClientConfig.parse_headers_from_env(123)  # type: ignore[arg-type]


def test_client_config_resolve_base_url_from_env_defaults_and_rejects_blank():
    assert ClientConfig.resolve_base_url_from_env(None) == "https://api.hyperbrowser.ai"
    assert (
        ClientConfig.resolve_base_url_from_env("https://example.local")
        == "https://example.local"
    )
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        ClientConfig.resolve_base_url_from_env("   ")
    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig.resolve_base_url_from_env("https://")
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must be a string"
    ):
        ClientConfig.resolve_base_url_from_env(123)  # type: ignore[arg-type]


def test_client_config_normalize_base_url_validates_and_normalizes():
    assert (
        ClientConfig.normalize_base_url(" https://example.local/custom/api/ ")
        == "https://example.local/custom/api"
    )
    assert (
        ClientConfig.normalize_base_url("https://example.local:443/custom/api")
        == "https://example.local:443/custom/api"
    )

    with pytest.raises(HyperbrowserError, match="base_url must be a string"):
        ClientConfig.normalize_base_url(None)  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="base_url must not be empty"):
        ClientConfig.normalize_base_url("   ")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig.normalize_base_url("example.local")
    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig.normalize_base_url("https://:443")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig.normalize_base_url("https://example.local:99999")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig.normalize_base_url("https://example.local:bad")

    with pytest.raises(HyperbrowserError, match="must not include query parameters"):
        ClientConfig.normalize_base_url("https://example.local?foo=bar")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain newline characters"
    ):
        ClientConfig.normalize_base_url("https://example.local/\napi")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain whitespace characters"
    ):
        ClientConfig.normalize_base_url("https://example.local/\tapi")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain backslashes"
    ):
        ClientConfig.normalize_base_url("https://example.local\\api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain control characters"
    ):
        ClientConfig.normalize_base_url("https://example.local\x00api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not include user credentials"
    ):
        ClientConfig.normalize_base_url("https://user:pass@example.local")


def test_client_config_normalize_base_url_wraps_unexpected_urlparse_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_runtime_error(_value: str):
        raise RuntimeError("url parser exploded")

    monkeypatch.setattr(config_module, "urlparse", _raise_runtime_error)

    with pytest.raises(HyperbrowserError, match="Failed to parse base_url") as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_preserves_hyperbrowser_urlparse_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_hyperbrowser_error(_value: str):
        raise HyperbrowserError("custom urlparse failure")

    monkeypatch.setattr(config_module, "urlparse", _raise_hyperbrowser_error)

    with pytest.raises(HyperbrowserError, match="custom urlparse failure") as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is None


def test_client_config_normalize_base_url_wraps_component_access_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        @property
        def scheme(self):
            raise RuntimeError("scheme parser exploded")

        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="Failed to parse base_url components"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_preserves_hyperbrowser_component_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        @property
        def scheme(self):
            raise HyperbrowserError("custom component failure")

        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="custom component failure"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is None


def test_client_config_normalize_base_url_rejects_invalid_urlparse_component_types(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = object()
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_string_subclass_components(
    monkeypatch: pytest.MonkeyPatch,
):
    class _WeirdString(str):
        pass

    class _ParsedURL:
        scheme = _WeirdString("https")
        netloc = _WeirdString("example.local")
        hostname = "example.local"
        query = _WeirdString("")
        fragment = _WeirdString("")
        username = None
        password = None
        path = _WeirdString("/api")

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_invalid_hostname_types(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = object()
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_invalid_username_types(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = object()
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_invalid_password_types(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = object()
        path = "/api"

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_invalid_port_types(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self):
            return "443"

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_boolean_port_values(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self):
            return True

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_invalid_query_component_types(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = object()
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_out_of_range_port_values(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return 70000

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_rejects_negative_port_values(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def port(self) -> int:
            return -1

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url parser returned invalid URL components"
    ):
        ClientConfig.normalize_base_url("https://example.local")


def test_client_config_normalize_base_url_wraps_hostname_access_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def hostname(self):
            raise RuntimeError("hostname parser exploded")

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="Failed to parse base_url host"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_wraps_credential_access_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        path = "/api"

        @property
        def username(self):
            raise RuntimeError("credential parser exploded")

        @property
        def password(self):
            return None

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="Failed to parse base_url credentials"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_preserves_hyperbrowser_hostname_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = "/api"

        @property
        def hostname(self):
            raise HyperbrowserError("custom hostname parser failure")

        @property
        def port(self) -> int:
            return 443

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="custom hostname parser failure"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is None


def test_client_config_normalize_base_url_wraps_path_decode_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_runtime_error(_value: str) -> str:
        raise RuntimeError("path decode exploded")

    monkeypatch.setattr(config_module, "unquote", _raise_runtime_error)

    with pytest.raises(
        HyperbrowserError, match="Failed to decode base_url path"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local/api")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_wraps_host_decode_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _conditional_unquote(value: str) -> str:
        if value == "example.local":
            raise RuntimeError("host decode exploded")
        return value

    monkeypatch.setattr(config_module, "unquote", _conditional_unquote)

    with pytest.raises(
        HyperbrowserError, match="Failed to decode base_url host"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local/api")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_preserves_hyperbrowser_decode_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_hyperbrowser_error(_value: str) -> str:
        raise HyperbrowserError("custom decode failure")

    monkeypatch.setattr(config_module, "unquote", _raise_hyperbrowser_error)

    with pytest.raises(HyperbrowserError, match="custom decode failure") as exc_info:
        ClientConfig.normalize_base_url("https://example.local/api")

    assert exc_info.value.original_error is None


def test_client_config_normalize_base_url_wraps_non_string_decode_results(
    monkeypatch: pytest.MonkeyPatch,
):
    def _return_bytes(_value: str) -> bytes:
        return b"/api"

    monkeypatch.setattr(config_module, "unquote", _return_bytes)

    with pytest.raises(
        HyperbrowserError, match="Failed to decode base_url path"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local/api")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_rejects_string_subclass_decode_results(
    monkeypatch: pytest.MonkeyPatch,
):
    class _WeirdString(str):
        pass

    def _return_weird_string(_value: str) -> str:
        return _WeirdString("/api")

    monkeypatch.setattr(config_module, "unquote", _return_weird_string)

    with pytest.raises(
        HyperbrowserError, match="Failed to decode base_url path"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local/api")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_preserves_invalid_port_original_error():
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local:bad")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_wraps_unexpected_port_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = ""

        @property
        def port(self) -> int:
            raise RuntimeError("unexpected port parser failure")

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is not None


def test_client_config_normalize_base_url_preserves_hyperbrowser_port_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _ParsedURL:
        scheme = "https"
        netloc = "example.local"
        hostname = "example.local"
        query = ""
        fragment = ""
        username = None
        password = None
        path = ""

        @property
        def port(self) -> int:
            raise HyperbrowserError("custom port parser failure")

    monkeypatch.setattr(config_module, "urlparse", lambda _value: _ParsedURL())

    with pytest.raises(
        HyperbrowserError, match="custom port parser failure"
    ) as exc_info:
        ClientConfig.normalize_base_url("https://example.local")

    assert exc_info.value.original_error is None


def test_client_config_normalize_base_url_rejects_encoded_paths_and_hosts():
    with pytest.raises(
        HyperbrowserError, match="base_url path must not contain relative path segments"
    ):
        ClientConfig.normalize_base_url("https://example.local/%252e%252e/api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain backslashes"
    ):
        ClientConfig.normalize_base_url("https://example.local/%255Capi")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain whitespace characters"
    ):
        ClientConfig.normalize_base_url("https://example.local/%2520api")
    with pytest.raises(
        HyperbrowserError, match="base_url host must not contain backslashes"
    ):
        ClientConfig.normalize_base_url("https://example.local%255C")
    with pytest.raises(
        HyperbrowserError, match="base_url host must not contain whitespace characters"
    ):
        ClientConfig.normalize_base_url("https://example.local%2520")
    with pytest.raises(
        HyperbrowserError, match="base_url host must not contain control characters"
    ):
        ClientConfig.normalize_base_url("https://example.local%2500")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host must not contain encoded delimiter characters",
    ):
        ClientConfig.normalize_base_url("https://example.local%252Fapi")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host must not contain encoded delimiter characters",
    ):
        ClientConfig.normalize_base_url("https://example.local%2540attacker.com")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host must not contain encoded delimiter characters",
    ):
        ClientConfig.normalize_base_url("https://example.local%253A443")
    with pytest.raises(
        HyperbrowserError,
        match="base_url path must not contain encoded query or fragment delimiters",
    ):
        ClientConfig.normalize_base_url("https://example.local/%253Fapi")
    bounded_encoded_host_label = "%61"
    for _ in range(9):
        bounded_encoded_host_label = quote(bounded_encoded_host_label, safe="")
    assert (
        ClientConfig.normalize_base_url(
            f"https://{bounded_encoded_host_label}.example.local"
        )
        == f"https://{bounded_encoded_host_label}.example.local"
    )
    deeply_encoded_dot = "%2e"
    for _ in range(11):
        deeply_encoded_dot = quote(deeply_encoded_dot, safe="")
    with pytest.raises(
        HyperbrowserError,
        match="base_url path contains excessively nested URL encoding",
    ):
        ClientConfig.normalize_base_url(
            f"https://example.local/{deeply_encoded_dot}/api"
        )
    deeply_encoded_host_label = "%61"
    for _ in range(11):
        deeply_encoded_host_label = quote(deeply_encoded_host_label, safe="")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host contains excessively nested URL encoding",
    ):
        ClientConfig.normalize_base_url(
            f"https://{deeply_encoded_host_label}.example.local"
        )
