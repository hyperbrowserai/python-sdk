from typing import FrozenSet

DEFAULT_TERMINAL_JOB_STATUSES: FrozenSet[str] = frozenset({"completed", "failed"})


def is_default_terminal_job_status(status: str) -> bool:
    return status in DEFAULT_TERMINAL_JOB_STATUSES
