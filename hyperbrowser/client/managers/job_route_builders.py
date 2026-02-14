def build_job_route(
    route_prefix: str,
    job_id: str,
) -> str:
    return f"{route_prefix}/{job_id}"


def build_job_status_route(
    route_prefix: str,
    job_id: str,
) -> str:
    return f"{route_prefix}/{job_id}/status"


def build_job_action_route(
    route_prefix: str,
    job_id: str,
    action_suffix: str,
) -> str:
    return f"{route_prefix}/{job_id}{action_suffix}"
