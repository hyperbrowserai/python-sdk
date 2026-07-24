# Migrating to Hyperbrowser Python SDK 1.0

Hyperbrowser Python SDK 1.0 makes plain dictionaries the preferred way to pass
request parameters. Public method signatures use `TypedDict` definitions, which
gives editors autocomplete and static checking inside both top-level and nested
dictionary literals.

The wire format and response model behavior are unchanged. Existing Pydantic
request objects remain supported, so most applications can upgrade before
migrating individual call sites.

## Upgrade

```shell
pip install --upgrade "hyperbrowser>=1.0,<2"
```

## Request parameters

New and updated code should pass dictionaries:

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")
session = client.sessions.create(
    {
        "use_stealth": True,
        "screen": {"width": 1920, "height": 1080},
    }
)
```

The equivalent pre-1.0 Pydantic request remains valid:

```python
from hyperbrowser.models import CreateSessionParams

session = client.sessions.create(
    CreateSessionParams(
        use_stealth=True,
        screen={"width": 1920, "height": 1080},
    )
)
```

You do not need to migrate all call sites at once. Dictionary and legacy-model
requests can coexist in the same application.

## Importing request types

Request `TypedDict` definitions live in `hyperbrowser.types`:

```python
from hyperbrowser.types import CreateSessionParams

params: CreateSessionParams = {
    "use_stealth": True,
    "screen": {"width": 1920, "height": 1080},
}
session = client.sessions.create(params)
```

The same name imported from `hyperbrowser.models` is the legacy Pydantic class.
Use an alias if both forms are needed in one module:

```python
from hyperbrowser.models import CreateSessionParams as LegacyCreateSessionParams
from hyperbrowser.types import CreateSessionParams
```

## Request and response behavior

- Use Pythonic `snake_case` request keys. The SDK translates its own fields to
  the API's wire aliases.
- Pass only the fields you need. Dictionaries are validated when the SDK method
  is called.
- Responses are still Pydantic models and retain methods such as
  `model_dump()` and `model_dump_json()`.
- If your code relies on constructing and validating a request before making an
  SDK call, it can continue using the legacy class from `hyperbrowser.models`.

The same rules apply to `Hyperbrowser` and `AsyncHyperbrowser`.

## JSON Schema and user-owned dictionaries

Pass JSON Schema directly to fields such as `schema` and
`output_model_schema`:

```python
result = client.extract.start_and_wait(
    {
        "urls": ["https://example.com"],
        "prompt": "Extract the product name and price.",
        "schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "price_in_usd": {"type": "number"},
            },
            "required": ["product_name", "price_in_usd"],
        },
    }
)
```

Schema content is treated as user-owned data. Keys such as `$defs`, `$ref`,
`product_name`, and custom extension keywords are not converted to camel case.
The same preservation rule applies to other open mappings such as environment
variables, storage state, sensitive data, and agent action payloads.

Endpoints that support boolean JSON Schemas also accept `True` and `False`
directly.

Where a schema field is documented as supporting it, a Pydantic model class can
still be supplied and the SDK will generate its JSON Schema.

## Compatibility checklist

When upgrading:

1. Upgrade the package and run your existing tests; legacy request objects
   should continue to work.
2. Update new or frequently edited request call sites to dictionaries.
3. Import named request annotations from `hyperbrowser.types`, not
   `hyperbrowser.models`.
4. Keep importing response models and any intentionally retained legacy request
   classes from `hyperbrowser.models`.
5. Run your type checker to catch misspelled or invalid nested request keys.

No response-model migration is required for 1.0.
