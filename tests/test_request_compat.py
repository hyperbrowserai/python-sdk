from copy import deepcopy

import pytest
from pydantic import BaseModel, ValidationError

from hyperbrowser.client._request import (
    dump_request,
    normalize_pydantic_schema,
)
from hyperbrowser.models import (
    CreateSandboxParams,
    CreateSessionParams,
    StartBrowserUseTaskParams,
)
from hyperbrowser.tools import _normalize_extract_tool_params


def test_mapping_and_legacy_model_produce_identical_session_payloads():
    mapping = {
        "use_stealth": True,
        "screen": {"width": 1920, "height": 1080},
        "start_from_snapshot": {"snapshot_id": "snapshot-123"},
    }
    legacy = CreateSessionParams(**mapping)

    assert dump_request(mapping, CreateSessionParams) == dump_request(
        legacy,
        CreateSessionParams,
    )
    assert dump_request(mapping, CreateSessionParams) == {
        "useUltraStealth": False,
        "useStealth": True,
        "useProxy": False,
        "locales": ["en"],
        "screen": {"width": 1920, "height": 1080},
        "solveCaptchas": False,
        "adblock": False,
        "trackers": False,
        "annoyances": False,
        "startFromSnapshot": {"snapshotId": "snapshot-123"},
    }


def test_mapping_normalization_does_not_mutate_nested_open_mappings():
    mapping = {
        "task": "log in",
        "initial_actions": [
            {
                "custom_action": {
                    "snake_case_key": None,
                    "camelCaseKey": "unchanged",
                }
            }
        ],
        "sensitive_data": {
            "x_user": "person@example.com",
            "API_TOKEN": "secret",
        },
    }
    original = deepcopy(mapping)

    payload = dump_request(mapping, StartBrowserUseTaskParams)

    assert mapping == original
    assert payload["initialActions"] == original["initial_actions"]
    assert payload["sensitiveData"] == original["sensitive_data"]


def test_mapping_uses_existing_cross_field_validation():
    with pytest.raises(ValidationError, match="exactly one start source"):
        dump_request(
            {"image_name": "node", "snapshot_name": "snapshot"},
            CreateSandboxParams,
        )


def test_raw_json_schema_is_copied_without_rewriting_or_dereferencing():
    schema = {
        "$defs": {
            "snake_case_name": {
                "type": "object",
                "properties": {
                    "keep_this_name": {"type": ["string", "null"], "default": None}
                },
            }
        },
        "$ref": "#/$defs/snake_case_name",
        "x-custom-keyword": {"camelCase": None},
    }
    original = deepcopy(schema)

    normalized = normalize_pydantic_schema(schema)

    assert normalized == original
    assert normalized is not schema
    assert schema == original


def test_pydantic_schema_provider_is_dereferenced_without_mutating_class():
    class Address(BaseModel):
        postal_code: str

    class Person(BaseModel):
        address: Address

    normalized = normalize_pydantic_schema(Person)

    assert "$ref" not in normalized["properties"]["address"]
    assert normalized["properties"]["address"]["properties"]["postal_code"] == {
        "title": "Postal Code",
        "type": "string",
    }


def test_extract_tool_schema_string_is_parsed_without_mutating_input():
    params = {
        "urls": ["https://example.com"],
        "schema": '{"type":"object","properties":{"snake_case":{"type":"string"}}}',
    }
    original = deepcopy(params)

    normalized = _normalize_extract_tool_params(params)

    assert params == original
    assert normalized["schema"] == {
        "type": "object",
        "properties": {"snake_case": {"type": "string"}},
    }
