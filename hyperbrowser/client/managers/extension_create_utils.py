from typing import Any, Dict, Tuple

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams

from ..file_utils import build_file_path_error_message, ensure_existing_file_path
from .extension_operation_metadata import EXTENSION_OPERATION_METADATA
from .serialization_utils import serialize_model_dump_to_dict


def normalize_extension_create_input(params: Any) -> Tuple[str, Dict[str, Any]]:
    if type(params) is not CreateExtensionParams:
        raise HyperbrowserError("params must be CreateExtensionParams")
    try:
        raw_file_path = params.file_path
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "params.file_path is invalid",
            original_error=exc,
        ) from exc

    payload = serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize extension create params",
    )
    payload.pop("filePath", None)

    file_path = ensure_existing_file_path(
        raw_file_path,
        missing_file_message=build_file_path_error_message(
            raw_file_path,
            prefix=EXTENSION_OPERATION_METADATA.missing_file_message_prefix,
            default_prefix="Extension file not found at path",
        ),
        not_file_message=build_file_path_error_message(
            raw_file_path,
            prefix=EXTENSION_OPERATION_METADATA.not_file_message_prefix,
            default_prefix="Extension file path must point to a file",
        ),
    )
    return file_path, payload
