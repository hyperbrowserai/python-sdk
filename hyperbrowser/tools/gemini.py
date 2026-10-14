"""Gemini declaration for credential fill, using the shared descriptions."""

from copy import deepcopy

from .schema import FILL_CREDENTIAL_DESCRIPTION, FILL_CREDENTIAL_SCHEMA

_properties = FILL_CREDENTIAL_SCHEMA["properties"]


def _nullable_string(description):
    return {"type": "string", "nullable": True, "description": description}


FILL_CREDENTIAL_TOOL_GEMINI = deepcopy(
    {
        "name": "fill_credential",
        "description": FILL_CREDENTIAL_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                **{
                    name: _nullable_string(_properties[name]["description"])
                    for name in (
                        "credential",
                        "vault",
                        "page_id",
                        "page_url",
                        "frame_url",
                    )
                },
                "fields": {
                    "type": "array",
                    "description": _properties["fields"]["description"],
                    "minItems": _properties["fields"]["minItems"],
                    "maxItems": _properties["fields"]["maxItems"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "selector": _properties["fields"]["items"]["properties"][
                                "selector"
                            ],
                            "field": _nullable_string(
                                _properties["fields"]["items"]["properties"]["field"][
                                    "description"
                                ]
                            ),
                        },
                        "required": _properties["fields"]["items"]["required"],
                    },
                },
            },
            "required": FILL_CREDENTIAL_SCHEMA["required"],
        },
    }
)
