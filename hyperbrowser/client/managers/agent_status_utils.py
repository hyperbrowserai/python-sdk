from typing import FrozenSet

AGENT_TERMINAL_STATUSES: FrozenSet[str] = frozenset(
    {"completed", "failed", "stopped"}
)


def is_agent_terminal_status(status: str) -> bool:
    return status in AGENT_TERMINAL_STATUSES
