from hyperbrowser.sandbox_common import (
    resolve_runtime_transport_target,
    to_websocket_transport_target,
)


def test_runtime_transport_target_ignores_ambient_proxy_without_explicit_override(
    monkeypatch,
):
    monkeypatch.setenv("REGIONAL_PROXY_DEV_HOST", "http://127.0.0.1:8090")

    target = resolve_runtime_transport_target(
        "https://session.example.dev:8443",
        "/sandbox/exec?foo=bar",
    )

    assert target.url == "https://session.example.dev:8443/sandbox/exec?foo=bar"
    assert target.host_header is None


def test_runtime_transport_target_applies_explicit_proxy_override():
    target = resolve_runtime_transport_target(
        "https://session.example.dev:8443",
        "/sandbox/exec?foo=bar",
        "http://127.0.0.1:8090",
    )

    assert target.url == "http://127.0.0.1:8090/sandbox/exec?foo=bar"
    assert target.host_header == "session.example.dev:8443"


def test_runtime_websocket_target_applies_explicit_proxy_override():
    target = to_websocket_transport_target(
        "https://session.example.dev:8443",
        "/sandbox/pty/pty_123/ws?sessionId=sandbox_123",
        "http://127.0.0.1:8090",
    )

    assert (
        target.url
        == "wss://session.example.dev:8443/sandbox/pty/pty_123/ws?sessionId=sandbox_123"
    )
    assert target.connect_host == "127.0.0.1"
    assert target.connect_port == 8090
