import pytest
from pydantic import ValidationError

from hyperbrowser.models.session import Session


def _build_session_payload() -> dict:
    return {
        "id": "session-1",
        "teamId": "team-1",
        "status": "active",
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-01T00:00:00Z",
        "sessionUrl": "https://example.com/session/1",
        "proxyDataConsumed": "0",
    }


def test_session_model_converts_plain_string_timestamps_to_int():
    payload = _build_session_payload()
    payload["startTime"] = "1735689600"
    payload["endTime"] = "1735689660"

    model = Session.model_validate(payload)

    assert model.start_time == 1735689600
    assert model.end_time == 1735689660


def test_session_model_rejects_string_subclass_timestamps():
    class _TimestampString(str):
        pass

    payload = _build_session_payload()
    payload["startTime"] = _TimestampString("1735689600")

    with pytest.raises(
        ValidationError, match="timestamp string values must be plain strings"
    ):
        Session.model_validate(payload)


def test_session_model_rejects_boolean_timestamps():
    payload = _build_session_payload()
    payload["startTime"] = True

    with pytest.raises(
        ValidationError,
        match="timestamp values must be integers or plain numeric strings",
    ):
        Session.model_validate(payload)


def test_session_model_preserves_integer_timestamps():
    payload = _build_session_payload()
    payload["startTime"] = 1735689600
    payload["endTime"] = 1735689660

    model = Session.model_validate(payload)

    assert model.start_time == 1735689600
    assert model.end_time == 1735689660


def test_session_model_rejects_integer_subclass_timestamps():
    class _TimestampInt(int):
        pass

    payload = _build_session_payload()
    payload["startTime"] = _TimestampInt(1735689600)

    with pytest.raises(
        ValidationError,
        match="timestamp values must be plain integers or plain numeric strings",
    ):
        Session.model_validate(payload)


def test_session_model_rejects_non_integer_timestamp_strings():
    payload = _build_session_payload()
    payload["startTime"] = "not-a-number"

    with pytest.raises(
        ValidationError, match="timestamp string values must be integer-formatted"
    ):
        Session.model_validate(payload)


def test_session_model_rejects_float_timestamps():
    payload = _build_session_payload()
    payload["startTime"] = 1.0

    with pytest.raises(
        ValidationError,
        match="timestamp values must be plain integers or plain numeric strings",
    ):
        Session.model_validate(payload)
