import asyncio

import hyperbrowser.client.managers.profile_request_utils as profile_request_utils


def test_create_profile_resource_delegates_to_post_model_request():
    captured = {}

    def _fake_post_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.post_model_request
    profile_request_utils.post_model_request = _fake_post_model_request
    try:
        result = profile_request_utils.create_profile_resource(
            client=object(),
            route_prefix="/profile",
            payload={"name": "test"},
            model=object,
            operation_name="create profile",
        )
    finally:
        profile_request_utils.post_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profile"
    assert captured["data"] == {"name": "test"}
    assert captured["operation_name"] == "create profile"


def test_get_profile_resource_delegates_to_get_model_request():
    captured = {}

    def _fake_get_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.get_model_request
    profile_request_utils.get_model_request = _fake_get_model_request
    try:
        result = profile_request_utils.get_profile_resource(
            client=object(),
            profile_id="profile-2",
            model=object,
            operation_name="get profile",
        )
    finally:
        profile_request_utils.get_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profile/profile-2"
    assert captured["params"] is None
    assert captured["operation_name"] == "get profile"


def test_delete_profile_resource_delegates_to_delete_model_request():
    captured = {}

    def _fake_delete_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.delete_model_request
    profile_request_utils.delete_model_request = _fake_delete_model_request
    try:
        result = profile_request_utils.delete_profile_resource(
            client=object(),
            profile_id="profile-3",
            model=object,
            operation_name="delete profile",
        )
    finally:
        profile_request_utils.delete_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profile/profile-3"
    assert captured["operation_name"] == "delete profile"


def test_list_profile_resources_delegates_to_get_model_request():
    captured = {}

    def _fake_get_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.get_model_request
    profile_request_utils.get_model_request = _fake_get_model_request
    try:
        result = profile_request_utils.list_profile_resources(
            client=object(),
            list_route_path="/profiles",
            params={"page": 1},
            model=object,
            operation_name="list profiles",
        )
    finally:
        profile_request_utils.get_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profiles"
    assert captured["params"] == {"page": 1}
    assert captured["operation_name"] == "list profiles"


def test_create_profile_resource_async_delegates_to_post_model_request_async():
    captured = {}

    async def _fake_post_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.post_model_request_async
    profile_request_utils.post_model_request_async = _fake_post_model_request_async
    try:
        result = asyncio.run(
            profile_request_utils.create_profile_resource_async(
                client=object(),
                route_prefix="/profile",
                payload={"name": "async"},
                model=object,
                operation_name="create profile",
            )
        )
    finally:
        profile_request_utils.post_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profile"
    assert captured["data"] == {"name": "async"}
    assert captured["operation_name"] == "create profile"


def test_get_profile_resource_async_delegates_to_get_model_request_async():
    captured = {}

    async def _fake_get_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.get_model_request_async
    profile_request_utils.get_model_request_async = _fake_get_model_request_async
    try:
        result = asyncio.run(
            profile_request_utils.get_profile_resource_async(
                client=object(),
                profile_id="profile-5",
                model=object,
                operation_name="get profile",
            )
        )
    finally:
        profile_request_utils.get_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profile/profile-5"
    assert captured["params"] is None
    assert captured["operation_name"] == "get profile"


def test_delete_profile_resource_async_delegates_to_delete_model_request_async():
    captured = {}

    async def _fake_delete_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.delete_model_request_async
    profile_request_utils.delete_model_request_async = _fake_delete_model_request_async
    try:
        result = asyncio.run(
            profile_request_utils.delete_profile_resource_async(
                client=object(),
                profile_id="profile-6",
                model=object,
                operation_name="delete profile",
            )
        )
    finally:
        profile_request_utils.delete_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profile/profile-6"
    assert captured["operation_name"] == "delete profile"


def test_list_profile_resources_async_delegates_to_get_model_request_async():
    captured = {}

    async def _fake_get_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = profile_request_utils.get_model_request_async
    profile_request_utils.get_model_request_async = _fake_get_model_request_async
    try:
        result = asyncio.run(
            profile_request_utils.list_profile_resources_async(
                client=object(),
                list_route_path="/profiles",
                params={"page": 2},
                model=object,
                operation_name="list profiles",
            )
        )
    finally:
        profile_request_utils.get_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/profiles"
    assert captured["params"] == {"page": 2}
    assert captured["operation_name"] == "list profiles"
