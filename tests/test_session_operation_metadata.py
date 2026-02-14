from hyperbrowser.client.managers.session_operation_metadata import (
    SESSION_OPERATION_METADATA,
)


def test_session_operation_metadata_values():
    assert SESSION_OPERATION_METADATA.event_logs_operation_name == "session event logs"
    assert SESSION_OPERATION_METADATA.detail_operation_name == "session detail"
    assert SESSION_OPERATION_METADATA.stop_operation_name == "session stop"
    assert SESSION_OPERATION_METADATA.list_operation_name == "session list"
    assert SESSION_OPERATION_METADATA.recording_url_operation_name == "session recording url"
    assert (
        SESSION_OPERATION_METADATA.video_recording_url_operation_name
        == "session video recording url"
    )
    assert (
        SESSION_OPERATION_METADATA.downloads_url_operation_name
        == "session downloads url"
    )
    assert SESSION_OPERATION_METADATA.upload_file_operation_name == "session upload file"
    assert SESSION_OPERATION_METADATA.extend_operation_name == "session extend"
    assert (
        SESSION_OPERATION_METADATA.update_profile_operation_name
        == "session update profile"
    )
