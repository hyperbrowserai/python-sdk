from hyperbrowser.client.managers.extension_route_constants import (
    EXTENSION_CREATE_ROUTE_PATH,
    EXTENSION_LIST_ROUTE_PATH,
)


def test_extension_route_constants_match_expected_api_paths():
    assert EXTENSION_CREATE_ROUTE_PATH == "/extensions/add"
    assert EXTENSION_LIST_ROUTE_PATH == "/extensions/list"
