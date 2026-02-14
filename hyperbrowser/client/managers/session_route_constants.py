SESSION_ROUTE_PREFIX = "/session"
SESSIONS_ROUTE_PATH = "/sessions"

SESSION_EVENT_LOGS_ROUTE_SUFFIX = "/event-logs"
SESSION_STOP_ROUTE_SUFFIX = "/stop"
SESSION_RECORDING_ROUTE_SUFFIX = "/recording"
SESSION_RECORDING_URL_ROUTE_SUFFIX = "/recording-url"
SESSION_VIDEO_RECORDING_URL_ROUTE_SUFFIX = "/video-recording-url"
SESSION_DOWNLOADS_URL_ROUTE_SUFFIX = "/downloads-url"
SESSION_UPLOADS_ROUTE_SUFFIX = "/uploads"
SESSION_EXTEND_ROUTE_SUFFIX = "/extend-session"
SESSION_UPDATE_ROUTE_SUFFIX = "/update"


def build_session_route(
    session_id: str,
    route_suffix: str = "",
) -> str:
    return f"{SESSION_ROUTE_PREFIX}/{session_id}{route_suffix}"
