from typing import Any, Type, Union, get_args, get_origin, get_type_hints

from hyperbrowser.client.managers.async_manager.profile import (
    ProfileManager as AsyncProfileManager,
)
from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.sync_manager.profile import (
    ProfileManager as SyncProfileManager,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)
from hyperbrowser.models.profile import CreateProfileParams
from hyperbrowser.models.session import CreateSessionParams


def _is_optional_annotation(annotation: Any, expected_type: Type[Any]) -> bool:
    if get_origin(annotation) is not Union:
        return False
    args = set(get_args(annotation))
    return expected_type in args and type(None) in args


def test_create_manager_param_annotations_are_optional():
    cases = [
        (SyncSessionManager.create, "params", CreateSessionParams),
        (AsyncSessionManager.create, "params", CreateSessionParams),
        (SyncProfileManager.create, "params", CreateProfileParams),
        (AsyncProfileManager.create, "params", CreateProfileParams),
    ]

    for method, param_name, expected_type in cases:
        type_hints = get_type_hints(method)
        assert _is_optional_annotation(type_hints[param_name], expected_type)
