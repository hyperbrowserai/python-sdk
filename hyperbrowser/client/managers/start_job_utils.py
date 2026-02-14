from typing import Optional, Tuple

from ..polling import build_operation_name, ensure_started_job_id


def build_started_job_context(
    *,
    started_job_id: Optional[str],
    start_error_message: str,
    operation_name_prefix: str,
) -> Tuple[str, str]:
    job_id = ensure_started_job_id(
        started_job_id,
        error_message=start_error_message,
    )
    operation_name = build_operation_name(operation_name_prefix, job_id)
    return job_id, operation_name
