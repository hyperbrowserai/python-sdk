from hyperbrowser.client.managers.profile_operation_metadata import (
    PROFILE_OPERATION_METADATA,
)


def test_profile_operation_metadata_values():
    assert PROFILE_OPERATION_METADATA.create_operation_name == "create profile"
    assert PROFILE_OPERATION_METADATA.get_operation_name == "get profile"
    assert PROFILE_OPERATION_METADATA.delete_operation_name == "delete profile"
    assert PROFILE_OPERATION_METADATA.list_operation_name == "list profiles"
