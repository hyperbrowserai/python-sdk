from hyperbrowser.client.managers.session_route_constants import (
    build_session_route,
    SESSION_DOWNLOADS_URL_ROUTE_SUFFIX,
    SESSION_EVENT_LOGS_ROUTE_SUFFIX,
    SESSION_EXTEND_ROUTE_SUFFIX,
    SESSION_RECORDING_ROUTE_SUFFIX,
    SESSION_RECORDING_URL_ROUTE_SUFFIX,
    SESSION_ROUTE_PREFIX,
    SESSION_STOP_ROUTE_SUFFIX,
    SESSION_UPDATE_ROUTE_SUFFIX,
    SESSION_UPLOADS_ROUTE_SUFFIX,
    SESSION_VIDEO_RECORDING_URL_ROUTE_SUFFIX,
    SESSIONS_ROUTE_PATH,
)


def test_session_route_constants_match_expected_api_paths():
    assert SESSION_ROUTE_PREFIX == "/session"
    assert SESSIONS_ROUTE_PATH == "/sessions"
    assert SESSION_EVENT_LOGS_ROUTE_SUFFIX == "/event-logs"
    assert SESSION_STOP_ROUTE_SUFFIX == "/stop"
    assert SESSION_RECORDING_ROUTE_SUFFIX == "/recording"
    assert SESSION_RECORDING_URL_ROUTE_SUFFIX == "/recording-url"
    assert SESSION_VIDEO_RECORDING_URL_ROUTE_SUFFIX == "/video-recording-url"
    assert SESSION_DOWNLOADS_URL_ROUTE_SUFFIX == "/downloads-url"
    assert SESSION_UPLOADS_ROUTE_SUFFIX == "/uploads"
    assert SESSION_EXTEND_ROUTE_SUFFIX == "/extend-session"
    assert SESSION_UPDATE_ROUTE_SUFFIX == "/update"


def test_build_session_route_composes_session_path_with_suffix():
    assert build_session_route("sess_123") == "/session/sess_123"
    assert (
        build_session_route("sess_123", SESSION_STOP_ROUTE_SUFFIX)
        == "/session/sess_123/stop"
    )
