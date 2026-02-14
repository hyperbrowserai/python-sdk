from hyperbrowser.client.managers.profile_route_constants import (
    build_profile_route,
    PROFILE_ROUTE_PREFIX,
    PROFILES_ROUTE_PATH,
)


def test_profile_route_constants_match_expected_api_paths():
    assert PROFILE_ROUTE_PREFIX == "/profile"
    assert PROFILES_ROUTE_PATH == "/profiles"


def test_build_profile_route_composes_profile_path():
    assert build_profile_route("profile_123") == "/profile/profile_123"
