from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileOperationMetadata:
    create_operation_name: str
    get_operation_name: str
    delete_operation_name: str
    list_operation_name: str


PROFILE_OPERATION_METADATA = ProfileOperationMetadata(
    create_operation_name="create profile",
    get_operation_name="get profile",
    delete_operation_name="delete profile",
    list_operation_name="list profiles",
)
