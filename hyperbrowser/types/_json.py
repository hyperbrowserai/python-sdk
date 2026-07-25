from typing import Any, Dict, Protocol, Type, Union

from typing_extensions import TypeAlias


JSONSchemaObject: TypeAlias = Dict[str, Any]
"""A user-provided JSON Schema object."""

JSONSchema: TypeAlias = Union[JSONSchemaObject, bool]
"""A JSON Schema object or boolean schema."""


class ModelJsonSchema(Protocol):
    """Structural type implemented by Pydantic model classes."""

    @classmethod
    def model_json_schema(cls) -> JSONSchemaObject: ...


JSONSchemaInput: TypeAlias = Union[JSONSchema, Type[ModelJsonSchema]]
"""A raw JSON Schema or a model class that can produce one."""

JSONSchemaObjectInput: TypeAlias = Union[JSONSchemaObject, Type[ModelJsonSchema]]
"""An object-form JSON Schema or a model class that can produce one."""


__all__ = [
    "JSONSchema",
    "JSONSchemaInput",
    "JSONSchemaObject",
    "JSONSchemaObjectInput",
    "ModelJsonSchema",
]
