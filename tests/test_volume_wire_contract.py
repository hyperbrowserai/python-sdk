import pytest

from hyperbrowser.client.managers.async_manager.volume import (
    VolumeManager as AsyncVolumeManager,
)
from hyperbrowser.client.managers.sync_manager.volume import VolumeManager
from hyperbrowser.models import CreateVolumeParams, Volume


VOLUME_PAYLOAD = {
    "id": "2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
    "name": "project-cache",
    "size": 0,
    "transferAmount": 0,
}

VOLUME_DETAIL_PAYLOAD = {
    "id": "2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
    "name": "project-cache",
}

VOLUME_LIST_PAYLOAD = {
    "volumes": [VOLUME_PAYLOAD],
}


class StubResponse:
    def __init__(self, data):
        self.data = data


class RecordingSyncTransport:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None, files=None):
        self.calls.append({"method": "POST", "url": url, "data": data, "files": files})
        return StubResponse(VOLUME_PAYLOAD)

    def get(self, url, params=None, follow_redirects=False):
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "params": params,
                "follow_redirects": follow_redirects,
            }
        )
        if url.endswith("/volume"):
            return StubResponse(VOLUME_LIST_PAYLOAD)
        if url.endswith(f"/volume/{VOLUME_DETAIL_PAYLOAD['id']}"):
            return StubResponse(VOLUME_DETAIL_PAYLOAD)
        return StubResponse({})


class RecordingAsyncTransport:
    def __init__(self):
        self.calls = []

    async def post(self, url, data=None, files=None):
        self.calls.append({"method": "POST", "url": url, "data": data, "files": files})
        return StubResponse(VOLUME_PAYLOAD)

    async def get(self, url, params=None, follow_redirects=False):
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "params": params,
                "follow_redirects": follow_redirects,
            }
        )
        if url.endswith("/volume"):
            return StubResponse(VOLUME_LIST_PAYLOAD)
        if url.endswith(f"/volume/{VOLUME_DETAIL_PAYLOAD['id']}"):
            return StubResponse(VOLUME_DETAIL_PAYLOAD)
        return StubResponse({})


class FakeSyncClient:
    def __init__(self):
        self.transport = RecordingSyncTransport()

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


class FakeAsyncClient:
    def __init__(self):
        self.transport = RecordingAsyncTransport()

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


def test_volume_models_serialize_and_parse_expected_wire_keys():
    assert CreateVolumeParams(name="project-cache").model_dump(
        by_alias=True, exclude_none=True
    ) == {
        "name": "project-cache",
    }

    parsed = Volume(
        id="2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
        name="project-cache",
        size="42",
        transferAmount="7",
    )
    assert parsed.size == 42
    assert parsed.transfer_amount == 7


def test_sync_volume_manager_uses_expected_wire_keys():
    client = FakeSyncClient()
    manager = VolumeManager(client)

    created = manager.create(CreateVolumeParams(name="project-cache"))
    listed = manager.list()
    fetched = manager.get("2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d")

    create_call = client.transport.calls[0]
    list_call = client.transport.calls[1]
    get_call = client.transport.calls[2]

    assert create_call["method"] == "POST"
    assert create_call["url"].endswith("/volume")
    assert create_call["data"] == {"name": "project-cache"}

    assert list_call["method"] == "GET"
    assert list_call["url"].endswith("/volume")
    assert listed.volumes[0].transfer_amount == 0

    assert get_call["method"] == "GET"
    assert get_call["url"].endswith("/volume/2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d")
    assert created.size == 0
    assert fetched.name == "project-cache"
    assert fetched.transfer_amount is None


@pytest.mark.anyio
async def test_async_volume_manager_uses_expected_wire_keys():
    client = FakeAsyncClient()
    manager = AsyncVolumeManager(client)

    created = await manager.create(CreateVolumeParams(name="project-cache"))
    listed = await manager.list()
    fetched = await manager.get("2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d")

    create_call = client.transport.calls[0]
    list_call = client.transport.calls[1]
    get_call = client.transport.calls[2]

    assert create_call["method"] == "POST"
    assert create_call["url"].endswith("/volume")
    assert create_call["data"] == {"name": "project-cache"}

    assert list_call["method"] == "GET"
    assert list_call["url"].endswith("/volume")
    assert listed.volumes[0].size == 0

    assert get_call["method"] == "GET"
    assert get_call["url"].endswith("/volume/2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d")
    assert created.transfer_amount == 0
    assert fetched.name == "project-cache"
