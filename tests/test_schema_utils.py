from pydantic import BaseModel

from hyperbrowser.client.schema_utils import inject_resolved_schema


class _SchemaModel(BaseModel):
    value: str


def test_inject_resolved_schema_sets_resolved_schema_value():
    payload = {"a": 1}

    inject_resolved_schema(payload, key="schema", schema_input=_SchemaModel)

    assert payload["schema"]["type"] == "object"
    assert "value" in payload["schema"]["properties"]


def test_inject_resolved_schema_ignores_none_schema_inputs():
    payload = {"a": 1}

    inject_resolved_schema(payload, key="schema", schema_input=None)

    assert payload == {"a": 1}
