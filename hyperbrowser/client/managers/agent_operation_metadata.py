from dataclasses import dataclass


@dataclass(frozen=True)
class AgentOperationMetadata:
    start_operation_name: str
    task_operation_name: str
    status_operation_name: str
    stop_operation_name: str
    start_error_message: str
    operation_name_prefix: str


BROWSER_USE_OPERATION_METADATA = AgentOperationMetadata(
    start_operation_name="browser-use start",
    task_operation_name="browser-use task",
    status_operation_name="browser-use task status",
    stop_operation_name="browser-use task stop",
    start_error_message="Failed to start browser-use task job",
    operation_name_prefix="browser-use task job ",
)

HYPER_AGENT_OPERATION_METADATA = AgentOperationMetadata(
    start_operation_name="hyper agent start",
    task_operation_name="hyper agent task",
    status_operation_name="hyper agent task status",
    stop_operation_name="hyper agent task stop",
    start_error_message="Failed to start HyperAgent task",
    operation_name_prefix="HyperAgent task ",
)

GEMINI_COMPUTER_USE_OPERATION_METADATA = AgentOperationMetadata(
    start_operation_name="gemini computer use start",
    task_operation_name="gemini computer use task",
    status_operation_name="gemini computer use task status",
    stop_operation_name="gemini computer use task stop",
    start_error_message="Failed to start Gemini Computer Use task job",
    operation_name_prefix="Gemini Computer Use task job ",
)

CLAUDE_COMPUTER_USE_OPERATION_METADATA = AgentOperationMetadata(
    start_operation_name="claude computer use start",
    task_operation_name="claude computer use task",
    status_operation_name="claude computer use task status",
    stop_operation_name="claude computer use task stop",
    start_error_message="Failed to start Claude Computer Use task job",
    operation_name_prefix="Claude Computer Use task job ",
)

CUA_OPERATION_METADATA = AgentOperationMetadata(
    start_operation_name="cua start",
    task_operation_name="cua task",
    status_operation_name="cua task status",
    stop_operation_name="cua task stop",
    start_error_message="Failed to start CUA task job",
    operation_name_prefix="CUA task job ",
)
