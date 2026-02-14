from dataclasses import dataclass


@dataclass(frozen=True)
class ComputerActionOperationMetadata:
    operation_name: str


COMPUTER_ACTION_OPERATION_METADATA = ComputerActionOperationMetadata(
    operation_name="computer action",
)
