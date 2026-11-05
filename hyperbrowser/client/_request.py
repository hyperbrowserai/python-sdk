import difflib
import warnings
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Dict, List, Optional, Type, TypeVar, get_args, get_origin

import jsonref
from pydantic import BaseModel


RequestModelT = TypeVar("RequestModelT", bound=BaseModel)


def _is_open(annotation: Any) -> bool:
    """True for annotations whose mapping values are user-owned data."""
    return (
        annotation is Any
        or annotation is dict
        or get_origin(annotation) in (dict, Mapping, type)
    )


def _nested_model(annotation: Any) -> Optional[Type[BaseModel]]:
    """Return the single request model wrapped by an annotation, if any.

    Unwraps Optional, List and similar containers. Returns None for open
    mappings and for unions of several models, which are left unchecked.
    """
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if _is_open(annotation):
        return None

    found = set()
    for arg in get_args(annotation):
        if _is_open(arg):
            # The field also accepts an open mapping or a class, so a mapping
            # value may be user-owned data (e.g. a JSON Schema). Skip it.
            return None
        nested = _nested_model(arg)
        if nested is not None:
            found.add(nested)
    return found.pop() if len(found) == 1 else None


def _unknown_keys(model: Type[BaseModel], data: Mapping, path: str) -> List[str]:
    """List keys in a request mapping that the model would silently drop."""
    if model.model_config.get("extra") in ("allow", "forbid"):
        # "allow" keeps extra keys and "forbid" already raises on them.
        return []

    config = model.model_config
    by_name = config.get("populate_by_name") or config.get("validate_by_name")
    by_alias = config.get("validate_by_alias", True)

    # Keys pydantic accepts on input, and the key to suggest for each field.
    accepted = {}
    preferred = {}
    for field_name, field in model.model_fields.items():
        inputs = []
        if field.alias is None or by_name:
            inputs.append(field_name)
        if by_alias:
            inputs += [a for a in (field.alias, field.validation_alias) if a]
        inputs = [a for a in inputs if isinstance(a, str)]
        for input_key in inputs:
            accepted[input_key] = field
        if inputs:
            for wire_name in (field_name, field.serialization_alias):
                if isinstance(wire_name, str) and wire_name not in accepted:
                    preferred[wire_name] = inputs[0]

    problems = []
    for key, item in data.items():
        if not isinstance(key, str):
            continue
        field = accepted.get(key)
        if field is None:
            if key in preferred:
                hint = f"use '{preferred[key]}'"
            else:
                close = difflib.get_close_matches(key, list(accepted), n=1)
                hint = f"did you mean '{close[0]}'?" if close else "unknown option"
            problems.append(f"'{path}{key}' ({hint})")
            continue

        nested = _nested_model(field.annotation)
        if nested is None:
            continue
        if isinstance(item, Mapping):
            problems.extend(_unknown_keys(nested, item, f"{path}{key}."))
        elif isinstance(item, (list, tuple)):
            for index, element in enumerate(item):
                if isinstance(element, Mapping):
                    problems.extend(
                        _unknown_keys(nested, element, f"{path}{key}[{index}].")
                    )
    return problems


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
        problems = _unknown_keys(model, value, "")
        if problems:
            warnings.warn(
                f"{model.__name__} ignored unrecognized {name} keys: "
                + ", ".join(problems)
                + ". These options were not sent to the API.",
                UserWarning,
                stacklevel=4,
            )
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
