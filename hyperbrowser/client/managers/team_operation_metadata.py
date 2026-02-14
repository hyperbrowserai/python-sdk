from dataclasses import dataclass


@dataclass(frozen=True)
class TeamOperationMetadata:
    get_credit_info_operation_name: str


TEAM_OPERATION_METADATA = TeamOperationMetadata(
    get_credit_info_operation_name="team credit info",
)
