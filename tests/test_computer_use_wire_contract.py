import pytest

from hyperbrowser.client.managers.agents_validation import validate_custom_api_keys
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    ClaudeComputerUseApiKeys,
    CuaApiKeys,
    GeminiComputerUseApiKeys,
    StartClaudeComputerUseTaskParams,
    StartCuaTaskParams,
    StartGeminiComputerUseTaskParams,
)


def test_cua_api_keys_serialize_openai_base_url() -> None:
    params = StartCuaTaskParams(
        task="go to example.com",
        use_custom_api_keys=True,
        api_keys=CuaApiKeys(
            openai="sk-test",
            openai_base_url="https://openai-compatible.example.com/v1",
        ),
    )

    assert params.model_dump(exclude_none=True, by_alias=True) == {
        "task": "go to example.com",
        "useCustomApiKeys": True,
        "apiKeys": {
            "openai": "sk-test",
            "openaiBaseUrl": "https://openai-compatible.example.com/v1",
        },
    }


def test_claude_computer_use_api_keys_serialize_anthropic_base_url() -> None:
    params = StartClaudeComputerUseTaskParams(
        task="go to example.com",
        use_custom_api_keys=True,
        api_keys=ClaudeComputerUseApiKeys(
            anthropic="sk-ant-test",
            anthropic_base_url="https://anthropic-compatible.example.com",
        ),
    )

    assert params.model_dump(exclude_none=True, by_alias=True) == {
        "task": "go to example.com",
        "useCustomApiKeys": True,
        "apiKeys": {
            "anthropic": "sk-ant-test",
            "anthropicBaseUrl": "https://anthropic-compatible.example.com",
        },
    }


def test_gemini_computer_use_api_keys_serialize_google_base_url() -> None:
    params = StartGeminiComputerUseTaskParams(
        task="go to example.com",
        use_custom_api_keys=True,
        api_keys=GeminiComputerUseApiKeys(
            google="google-test",
            google_base_url="https://gemini-compatible.example.com",
        ),
    )

    assert params.model_dump(exclude_none=True, by_alias=True) == {
        "task": "go to example.com",
        "useCustomApiKeys": True,
        "apiKeys": {
            "google": "google-test",
            "googleBaseUrl": "https://gemini-compatible.example.com",
        },
    }


def test_custom_api_key_mode_requires_api_keys() -> None:
    with pytest.raises(HyperbrowserError, match="api_keys must be provided"):
        validate_custom_api_keys(True, None, {})


def test_provider_base_urls_must_be_absolute_http_urls() -> None:
    with pytest.raises(HyperbrowserError, match="openai_base_url must be an absolute"):
        validate_custom_api_keys(False, None, {"openai_base_url": "localhost:3000/v1"})
