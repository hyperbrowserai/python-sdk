from typing import Any, List, Optional

import jsonref


def resolve_schema_input(schema_input: Any) -> Any:
    if hasattr(schema_input, "model_json_schema"):
        return jsonref.replace_refs(
            schema_input.model_json_schema(),
            proxies=False,
            lazy_load=False,
        )
    return schema_input


def inject_web_output_schemas(payload: dict, formats: Optional[List[Any]]) -> None:
    if not formats:
        return

    for index, output_format in enumerate(formats):
        schema_input = getattr(output_format, "schema_", None)
        if schema_input is None:
            continue
        payload["outputs"]["formats"][index]["schema"] = resolve_schema_input(
            schema_input
        )
