from hyperbrowser.client.managers.extension_operation_metadata import (
    EXTENSION_DEFAULT_MISSING_FILE_MESSAGE_PREFIX,
    EXTENSION_DEFAULT_NOT_FILE_MESSAGE_PREFIX,
    EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX,
    EXTENSION_OPERATION_METADATA,
)


def test_extension_operation_metadata_values():
    assert EXTENSION_OPERATION_METADATA.create_operation_name == "create extension"
    assert (
        EXTENSION_OPERATION_METADATA.missing_file_message_prefix
        == EXTENSION_DEFAULT_MISSING_FILE_MESSAGE_PREFIX
    )
    assert (
        EXTENSION_OPERATION_METADATA.not_file_message_prefix
        == EXTENSION_DEFAULT_NOT_FILE_MESSAGE_PREFIX
    )
    assert (
        EXTENSION_OPERATION_METADATA.open_file_error_prefix
        == EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX
    )
