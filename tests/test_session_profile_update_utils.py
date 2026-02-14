import pytest

from hyperbrowser.client.managers.session_profile_update_utils import (
    resolve_update_profile_params,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import UpdateSessionProfileParams


def test_resolve_update_profile_params_returns_plain_params_without_warning():
    warnings_triggered = 0

    def _on_deprecated_bool_usage() -> None:
        nonlocal warnings_triggered
        warnings_triggered += 1

    params = UpdateSessionProfileParams(persist_changes=True)
    result = resolve_update_profile_params(
        params,
        persist_changes=None,
        on_deprecated_bool_usage=_on_deprecated_bool_usage,
    )

    assert result is params
    assert warnings_triggered == 0


def test_resolve_update_profile_params_rejects_plain_params_with_keyword_argument():
    with pytest.raises(HyperbrowserError, match="not both"):
        resolve_update_profile_params(
            UpdateSessionProfileParams(persist_changes=True),
            persist_changes=True,
            on_deprecated_bool_usage=lambda: None,
        )


def test_resolve_update_profile_params_rejects_params_subclass():
    class _Params(UpdateSessionProfileParams):
        pass

    with pytest.raises(HyperbrowserError, match="plain UpdateSessionProfileParams"):
        resolve_update_profile_params(
            _Params(persist_changes=True),
            persist_changes=None,
            on_deprecated_bool_usage=lambda: None,
        )


def test_resolve_update_profile_params_builds_from_bool_and_warns():
    warnings_triggered = 0

    def _on_deprecated_bool_usage() -> None:
        nonlocal warnings_triggered
        warnings_triggered += 1

    result = resolve_update_profile_params(
        True,
        persist_changes=None,
        on_deprecated_bool_usage=_on_deprecated_bool_usage,
    )

    assert result.persist_changes is True
    assert warnings_triggered == 1


def test_resolve_update_profile_params_builds_from_keyword_bool_and_warns():
    warnings_triggered = 0

    def _on_deprecated_bool_usage() -> None:
        nonlocal warnings_triggered
        warnings_triggered += 1

    result = resolve_update_profile_params(
        None,
        persist_changes=False,
        on_deprecated_bool_usage=_on_deprecated_bool_usage,
    )

    assert result.persist_changes is False
    assert warnings_triggered == 1


def test_resolve_update_profile_params_requires_argument_or_keyword():
    with pytest.raises(HyperbrowserError, match="requires either"):
        resolve_update_profile_params(
            None,
            persist_changes=None,
            on_deprecated_bool_usage=lambda: None,
        )


def test_resolve_update_profile_params_rejects_unexpected_param_value():
    with pytest.raises(HyperbrowserError, match="requires either"):
        resolve_update_profile_params(  # type: ignore[arg-type]
            "true",
            persist_changes=None,
            on_deprecated_bool_usage=lambda: None,
        )
