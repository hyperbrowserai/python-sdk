import asyncio
import inspect
from copy import deepcopy
from types import SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.computer_action import (
    ComputerActionManager as AsyncComputerActionManager,
)
from hyperbrowser.client.managers.sync_manager.computer_action import (
    ComputerActionManager,
)
from hyperbrowser.models import (
    ClickActionParams,
    ComputerActionResponse,
    ComputerActionResponseDataClipboardText,
    ComputerActionResponseDataCursorPosition,
    ComputerActionResponseDataListWindows,
    CursorPositionActionParams,
    DragActionParams,
    ScrollActionParams,
)


@pytest.fixture(params=[ComputerActionManager, AsyncComputerActionManager])
def manager(request):
    calls = []
    session = SimpleNamespace(computer_action_endpoint="https://session.example/action")

    def get(session_id):
        calls.append(("get", session_id))
        return session

    def post(endpoint, *, data):
        calls.append(("post", endpoint, deepcopy(data)))
        payload = {"success": True}
        if data["action"] == "cursor_position":
            payload["data"] = {"x": 123, "y": 456}
        return SimpleNamespace(data=payload)

    async def async_get(session_id):
        return get(session_id)

    async def async_post(endpoint, *, data):
        return post(endpoint, data=data)

    is_async = request.param is AsyncComputerActionManager
    client = SimpleNamespace(
        sessions=SimpleNamespace(get=async_get if is_async else get),
        transport=SimpleNamespace(post=async_post if is_async else post),
    )
    return request.param(client), session, calls


def run(result):
    return asyncio.run(result) if inspect.isawaitable(result) else result


@pytest.mark.parametrize("by_id", [False, True])
def test_cursor_position_helper(manager, by_id):
    driver, session, calls = manager
    result = run(driver.cursor_position("session-id" if by_id else session, True))
    assert result.success
    assert isinstance(result.data, ComputerActionResponseDataCursorPosition)
    assert (result.data.x, result.data.y) == (123, 456)
    assert calls[-1] == (
        "post",
        session.computer_action_endpoint,
        {"action": "cursor_position", "returnScreenshot": True},
    )
    assert len(calls) == (2 if by_id else 1)


@pytest.mark.parametrize(
    "params",
    [
        {"action": "cursor_position", "return_screenshot": True},
        CursorPositionActionParams(return_screenshot=True),
    ],
)
def test_cursor_position_dict_and_model_requests(manager, params):
    driver, session, calls = manager
    result = run(driver._execute_request(session, params))
    assert isinstance(result.data, ComputerActionResponseDataCursorPosition)
    assert calls[-1][2] == {"action": "cursor_position", "returnScreenshot": True}


@pytest.mark.parametrize("action", ["click", "drag", "scroll"])
@pytest.mark.parametrize("keys", [None, [], ["Control_L", "Shift_L"]])
def test_pointer_modifier_helpers_and_existing_positional_arguments(
    manager, action, keys
):
    driver, session, calls = manager
    args = {
        "click": (10, 20, "right", 2, True),
        "drag": ([{"x": 10, "y": 20}, {"x": 30, "y": 40}], True),
        "scroll": (10, 20, 0, -2, True),
    }
    result = run(getattr(driver, action)(session, *args[action], keys=keys))
    assert result.success
    payload = calls[-1][2]
    assert payload["action"] == action
    assert payload["returnScreenshot"] is True
    if keys is None:
        assert "keys" not in payload
    else:
        assert payload["keys"] == keys
    if action == "click":
        assert (payload["button"], payload["numClicks"]) == ("right", 2)
    if action == "scroll":
        assert (payload["scrollX"], payload["scrollY"]) == (0, -2)


@pytest.mark.parametrize(
    "params, model",
    [
        ({"action": "click", "x": 10, "y": 20, "keys": ["Shift_L"]}, ClickActionParams),
        (
            {"action": "drag", "path": [{"x": 10, "y": 20}], "keys": ["Shift_L"]},
            DragActionParams,
        ),
        (
            {"action": "scroll", "scroll_x": 0, "scroll_y": 1, "keys": ["Shift_L"]},
            ScrollActionParams,
        ),
    ],
)
def test_modifier_dict_and_model_requests_match(manager, params, model):
    driver, session, calls = manager
    original = deepcopy(params)
    run(driver._execute_request(session, params))
    run(driver._execute_request(session, model(**params)))
    assert calls[-1] == calls[-2]
    assert calls[-1][2]["keys"] == ["Shift_L"]
    assert params == original


def test_scroll_at_current_cursor(manager):
    driver, session, calls = manager
    run(driver.scroll(session, scroll_y=2, keys=["Control_L"]))
    assert calls[-1][2] == {
        "action": "scroll",
        "scrollX": 0,
        "scrollY": 2,
        "returnScreenshot": False,
        "keys": ["Control_L"],
    }


@pytest.mark.parametrize("action", ["click", "drag", "scroll"])
def test_invalid_modifier_list_rejected_before_transport(manager, action):
    driver, session, calls = manager
    args = {"click": (), "drag": ([{"x": 10, "y": 20}],), "scroll": ()}
    with pytest.raises(ValueError):
        run(getattr(driver, action)(session, *args[action], keys="Shift_L"))
    assert not calls


@pytest.mark.parametrize(
    "data, model",
    [
        ({"x": 10, "y": 20}, ComputerActionResponseDataCursorPosition),
        ({"clipboardText": "hello"}, ComputerActionResponseDataClipboardText),
        (
            {
                "activeWindowId": "win",
                "windows": [{"id": "win", "name": "Chrome", "active": True}],
            },
            ComputerActionResponseDataListWindows,
        ),
    ],
)
def test_response_data_union_preserves_existing_actions(data, model):
    result = ComputerActionResponse(success=True, data=data)
    assert isinstance(result.data, model)
    assert result.data.model_dump(by_alias=True) == data


def test_new_request_and_response_types_are_public():
    import hyperbrowser.models as models
    import hyperbrowser.types as types

    assert "CursorPositionActionParams" in models.__all__
    assert "CursorPositionActionParams" in types.__all__
    assert "ComputerActionResponseDataCursorPosition" in models.__all__
