from hyperbrowser.client.managers.team_route_constants import (
    TEAM_CREDIT_INFO_ROUTE_PATH,
)


def test_team_route_constants_match_expected_api_paths():
    assert TEAM_CREDIT_INFO_ROUTE_PATH == "/team/credit-info"
