from dataclasses import dataclass


@dataclass(frozen=True)
class SessionOperationMetadata:
    event_logs_operation_name: str
    detail_operation_name: str
    stop_operation_name: str
    list_operation_name: str
    recording_url_operation_name: str
    video_recording_url_operation_name: str
    downloads_url_operation_name: str
    upload_file_operation_name: str
    upload_missing_file_message_prefix: str
    upload_not_file_message_prefix: str
    upload_open_file_error_prefix: str
    extend_operation_name: str
    update_profile_operation_name: str


SESSION_OPERATION_METADATA = SessionOperationMetadata(
    event_logs_operation_name="session event logs",
    detail_operation_name="session detail",
    stop_operation_name="session stop",
    list_operation_name="session list",
    recording_url_operation_name="session recording url",
    video_recording_url_operation_name="session video recording url",
    downloads_url_operation_name="session downloads url",
    upload_file_operation_name="session upload file",
    upload_missing_file_message_prefix="Upload file not found at path",
    upload_not_file_message_prefix="Upload file path must point to a file",
    upload_open_file_error_prefix="Failed to open upload file at path",
    extend_operation_name="session extend",
    update_profile_operation_name="session update profile",
)
