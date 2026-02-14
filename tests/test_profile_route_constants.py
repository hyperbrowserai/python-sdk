from hyperbrowser.client.managers.profile_route_constants import (
    PROFILE_ROUTE_PREFIX,
    PROFILES_ROUTE_PATH,
)


def test_profile_route_constants_match_expected_api_paths():
    assert PROFILE_ROUTE_PREFIX == "/profile"
    assert PROFILES_ROUTE_PATH == "/profiles"
