from hyperbrowser.client.managers.team_operation_metadata import (
    TEAM_OPERATION_METADATA,
)


def test_team_operation_metadata_values():
    assert TEAM_OPERATION_METADATA.get_credit_info_operation_name == "team credit info"
