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
    extend_operation_name="session extend",
    update_profile_operation_name="session update profile",
)
