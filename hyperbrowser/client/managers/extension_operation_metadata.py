from dataclasses import dataclass


@dataclass(frozen=True)
class ExtensionOperationMetadata:
    create_operation_name: str


EXTENSION_OPERATION_METADATA = ExtensionOperationMetadata(
    create_operation_name="create extension",
)
