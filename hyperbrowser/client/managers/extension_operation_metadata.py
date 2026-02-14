from dataclasses import dataclass


@dataclass(frozen=True)
class ExtensionOperationMetadata:
    create_operation_name: str
    missing_file_message_prefix: str
    not_file_message_prefix: str
    open_file_error_prefix: str


EXTENSION_OPERATION_METADATA = ExtensionOperationMetadata(
    create_operation_name="create extension",
    missing_file_message_prefix="Extension file not found at path",
    not_file_message_prefix="Extension file path must point to a file",
    open_file_error_prefix="Failed to open extension file at path",
)
