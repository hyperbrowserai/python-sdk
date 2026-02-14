from typing import Callable, Optional, Union

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import UpdateSessionProfileParams


def resolve_update_profile_params(
    params: Union[UpdateSessionProfileParams, bool, None],
    *,
    persist_changes: Optional[bool],
    on_deprecated_bool_usage: Callable[[], None],
) -> UpdateSessionProfileParams:
    if type(params) is UpdateSessionProfileParams:
        if persist_changes is not None:
            raise HyperbrowserError(
                "Pass either UpdateSessionProfileParams as the second argument or persist_changes=bool, not both."
            )
        return params
    if isinstance(params, UpdateSessionProfileParams):
        raise HyperbrowserError(
            "update_profile_params() requires a plain UpdateSessionProfileParams object."
        )
    if isinstance(params, bool):
        if persist_changes is not None:
            raise HyperbrowserError(
                "Pass either a boolean as the second argument or persist_changes=bool, not both."
            )
        on_deprecated_bool_usage()
        return UpdateSessionProfileParams(persist_changes=params)
    if params is None:
        if persist_changes is None:
            raise HyperbrowserError(
                "update_profile_params() requires either UpdateSessionProfileParams or persist_changes=bool."
            )
        on_deprecated_bool_usage()
        return UpdateSessionProfileParams(persist_changes=persist_changes)
    raise HyperbrowserError(
        "update_profile_params() requires either UpdateSessionProfileParams or a boolean persist_changes."
    )
