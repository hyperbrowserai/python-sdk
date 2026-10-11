import warnings

import pytest

from hyperbrowser.client._request import dump_request
from hyperbrowser.models import (
    CreateSandboxParams,
    CreateSessionParams,
    StartBrowserUseTaskParams,
    StartExtractJobParams,
    StartScrapeJobParams,
)


def _dump_without_warnings(mapping, model):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        return dump_request(mapping, model)


def test_misspelled_key_warns_with_suggestion():
    with pytest.warns(UserWarning) as record:
        payload = dump_request(
            {"use_stealth": True, "solve_captcha": True}, CreateSessionParams
        )

    message = str(record[0].message)
    assert "'solve_captcha' (did you mean 'solve_captchas'?)" in message
    assert "not sent to the API" in message
    # Behaviour is unchanged apart from the warning.
    assert payload["useStealth"] is True
    assert payload["solveCaptchas"] is False


def test_wire_name_key_warns_with_python_name():
    with pytest.warns(UserWarning) as record:
        payload = dump_request({"useStealth": True}, CreateSessionParams)

    assert "'useStealth' (use 'use_stealth')" in str(record[0].message)
    assert payload["useStealth"] is False


def test_nested_request_model_keys_are_checked():
    with pytest.warns(UserWarning) as record:
        dump_request(
            {
                "url": "https://example.com",
                "scrape_options": {"formats": ["markdown"], "only_main": True},
            },
            StartScrapeJobParams,
        )

    message = str(record[0].message)
    assert "'scrape_options.only_main' (did you mean 'only_main_content'?)" in message


def test_valid_mappings_do_not_warn():
    _dump_without_warnings(
        {
            "use_stealth": True,
            "solve_captchas": True,
            "screen": {"width": 1920, "height": 1080},
        },
        CreateSessionParams,
    )
    _dump_without_warnings(
        {
            "url": "https://example.com",
            "scrape_options": {"formats": ["markdown"], "only_main_content": True},
        },
        StartScrapeJobParams,
    )


def test_aliased_input_and_user_owned_mappings_do_not_warn():
    _dump_without_warnings(
        {
            "urls": ["https://example.com"],
            "schema": {"type": "object", "properties": {"anyKey": {}}},
        },
        StartExtractJobParams,
    )
    _dump_without_warnings(
        {
            "task": "log in",
            "initial_actions": [{"custom_action": {"snake_case_key": None}}],
        },
        StartBrowserUseTaskParams,
    )


def test_open_mapping_fields_do_not_warn():
    # Keys of a dict-typed field are user data, not option names.
    _dump_without_warnings(
        {"image_name": "node", "mounts": {"/workspace/cache": {"id": "vol_123"}}},
        CreateSandboxParams,
    )
    # A field that accepts either a JSON Schema dict or a model class.
    _dump_without_warnings(
        {
            "task": "extract",
            "output_model_schema": {"type": "object", "$defs": {}, "x-custom": 1},
        },
        StartBrowserUseTaskParams,
    )


def test_legacy_model_instances_do_not_warn():
    _dump_without_warnings(CreateSessionParams(use_stealth=True), CreateSessionParams)
