from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Dict, Type, TypeVar

import jsonref
from pydantic import BaseModel


RequestModelT = TypeVar("RequestModelT", bound=BaseModel)


def coerce_request(
    value: Any,
    model: Type[RequestModelT],
    *,
    name: str = "params",
) -> RequestModelT:
    """Validate a legacy request model or mapping without mutating caller state."""
    if isinstance(value, model):
        return value
    if isinstance(value, Mapping):
        return model.model_validate(dict(value))
    raise TypeError(
        f"{name} must be a {model.__name__} instance or mapping, "
        f"got {type(value).__name__}"
    )


def dump_request(
    value: Any,
    model: Type[RequestModelT],
    *,
    exclude_unset: bool = False,
    name: str = "params",
) -> Dict[str, Any]:
    """Validate and serialize a request using its existing wire contract."""
    normalized = coerce_request(value, model, name=name)
    return normalized.model_dump(
        by_alias=True,
        exclude_none=True,
        exclude_unset=exclude_unset,
    )


def normalize_pydantic_schema(value: Any) -> Any:
    """Copy a schema input, resolving refs only for Pydantic schema providers."""
    if hasattr(value, "model_json_schema"):
        return jsonref.replace_refs(
            value.model_json_schema(),
            proxies=False,
            lazy_load=False,
        )
    return deepcopy(value)


def dump_request_with_schema(
    value: Any,
    model: Type[RequestModelT],
    *,
    input_name: str,
    model_name: str,
    name: str = "params",
) -> Dict[str, Any]:
    """Serialize a request and normalize one caller-supplied JSON Schema field.

    Mapping inputs are pre-normalized when they contain a structural schema
    provider. This makes the public schema-provider protocol usable even when
    the backwards-compatible Pydantic request model only accepts BaseModel
    subclasses. A shallow model copy receives the normalized schema before
    serialization, preserving subclass field serializers without modifying the
    caller's request model or nested schema value.
    """
    prepared = value
    legacy_schema_provider = False
    if isinstance(value, model):
        legacy_schema_provider = hasattr(
            getattr(value, model_name),
            "model_json_schema",
        )
    elif isinstance(value, Mapping):
        schema = value.get(input_name)
        if hasattr(schema, "model_json_schema"):
            prepared = dict(value)
            prepared[input_name] = normalize_pydantic_schema(schema)

    normalized = coerce_request(prepared, model, name=name)
    if legacy_schema_provider:
        schema = normalize_pydantic_schema(getattr(normalized, model_name))
        normalized = normalized.model_copy()
        setattr(normalized, model_name, schema)
    return normalized.model_dump(by_alias=True, exclude_none=True)


def dump_request_with_fetch_schemas(
    value: Any,
    model: Type[RequestModelT],
    *,
    name: str = "params",
) -> Dict[str, Any]:
    """Serialize a web request and normalize nested JSON output schemas."""
    normalized = coerce_request(value, model, name=name)
    outputs = getattr(normalized, "outputs", None)
    formats = getattr(outputs, "formats", None)
    if outputs is not None and formats is not None:
        normalized_formats = []
        schemas_changed = False
        for output in formats:
            schema = getattr(output, "schema_", None)
            if getattr(output, "type", None) == "json" and hasattr(
                schema, "model_json_schema"
            ):
                normalized_schema = normalize_pydantic_schema(schema)
                output = output.model_copy()
                setattr(output, "schema_", normalized_schema)
                schemas_changed = True
            normalized_formats.append(output)

        if schemas_changed:
            normalized_outputs = outputs.model_copy(
                update={"formats": normalized_formats}
            )
            normalized = normalized.model_copy(update={"outputs": normalized_outputs})

    return normalized.model_dump(by_alias=True, exclude_none=True)
