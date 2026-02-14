from hyperbrowser.client.managers.session_operation_metadata import (
    SESSION_DEFAULT_UPLOAD_MISSING_FILE_MESSAGE_PREFIX,
    SESSION_DEFAULT_UPLOAD_NOT_FILE_MESSAGE_PREFIX,
    SESSION_DEFAULT_UPLOAD_OPEN_FILE_ERROR_PREFIX,
    SESSION_OPERATION_METADATA,
)


def test_session_operation_metadata_values():
    assert SESSION_OPERATION_METADATA.event_logs_operation_name == "session event logs"
    assert type(SESSION_OPERATION_METADATA.event_logs_operation_name) is str
    assert SESSION_OPERATION_METADATA.detail_operation_name == "session detail"
    assert type(SESSION_OPERATION_METADATA.detail_operation_name) is str
    assert SESSION_OPERATION_METADATA.stop_operation_name == "session stop"
    assert type(SESSION_OPERATION_METADATA.stop_operation_name) is str
    assert SESSION_OPERATION_METADATA.list_operation_name == "session list"
    assert type(SESSION_OPERATION_METADATA.list_operation_name) is str
    assert SESSION_OPERATION_METADATA.recording_url_operation_name == "session recording url"
    assert type(SESSION_OPERATION_METADATA.recording_url_operation_name) is str
    assert (
        SESSION_OPERATION_METADATA.video_recording_url_operation_name
        == "session video recording url"
    )
    assert type(SESSION_OPERATION_METADATA.video_recording_url_operation_name) is str
    assert (
        SESSION_OPERATION_METADATA.downloads_url_operation_name
        == "session downloads url"
    )
    assert type(SESSION_OPERATION_METADATA.downloads_url_operation_name) is str
    assert SESSION_OPERATION_METADATA.upload_file_operation_name == "session upload file"
    assert type(SESSION_OPERATION_METADATA.upload_file_operation_name) is str
    assert (
        SESSION_OPERATION_METADATA.upload_missing_file_message_prefix
        == SESSION_DEFAULT_UPLOAD_MISSING_FILE_MESSAGE_PREFIX
    )
    assert type(SESSION_OPERATION_METADATA.upload_missing_file_message_prefix) is str
    assert (
        SESSION_OPERATION_METADATA.upload_not_file_message_prefix
        == SESSION_DEFAULT_UPLOAD_NOT_FILE_MESSAGE_PREFIX
    )
    assert type(SESSION_OPERATION_METADATA.upload_not_file_message_prefix) is str
    assert (
        SESSION_OPERATION_METADATA.upload_open_file_error_prefix
        == SESSION_DEFAULT_UPLOAD_OPEN_FILE_ERROR_PREFIX
    )
    assert type(SESSION_OPERATION_METADATA.upload_open_file_error_prefix) is str
    assert SESSION_OPERATION_METADATA.extend_operation_name == "session extend"
    assert type(SESSION_OPERATION_METADATA.extend_operation_name) is str
    assert (
        SESSION_OPERATION_METADATA.update_profile_operation_name
        == "session update profile"
    )
    assert type(SESSION_OPERATION_METADATA.update_profile_operation_name) is str
