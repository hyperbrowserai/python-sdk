from hyperbrowser.client.managers.extension_operation_metadata import (
    EXTENSION_OPERATION_METADATA,
)


def test_extension_operation_metadata_values():
    assert EXTENSION_OPERATION_METADATA.create_operation_name == "create extension"
