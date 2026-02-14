from dataclasses import dataclass

EXTENSION_DEFAULT_MISSING_FILE_MESSAGE_PREFIX = "Extension file not found at path"
EXTENSION_DEFAULT_NOT_FILE_MESSAGE_PREFIX = "Extension file path must point to a file"
EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX = "Failed to open extension file at path"


@dataclass(frozen=True)
class ExtensionOperationMetadata:
    create_operation_name: str
    missing_file_message_prefix: str
    not_file_message_prefix: str
    open_file_error_prefix: str


EXTENSION_OPERATION_METADATA = ExtensionOperationMetadata(
    create_operation_name="create extension",
    missing_file_message_prefix=EXTENSION_DEFAULT_MISSING_FILE_MESSAGE_PREFIX,
    not_file_message_prefix=EXTENSION_DEFAULT_NOT_FILE_MESSAGE_PREFIX,
    open_file_error_prefix=EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX,
)
