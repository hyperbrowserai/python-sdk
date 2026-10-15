import pytest

from hyperbrowser.models.session import SessionEventLog


@pytest.mark.parametrize(
    "event_type", ["tab_opened", "credential_filled", "credential_fill_refused"]
)
def test_event_log_types_the_api_sends_parse(event_type):
    event = SessionEventLog.model_validate(
        {
            "id": "e1",
            "sessionId": "s1",
            "targetId": None,
            "pageUrl": "https://example.com/",
            "teamId": "t1",
            "type": event_type,
            "metadata": {},
            "timestamp": 1,
        }
    )
    assert event.type == event_type
