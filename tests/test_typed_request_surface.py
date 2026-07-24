import importlib
import inspect
from pathlib import Path
from typing import get_args, get_type_hints

from pydantic import BaseModel
from typing_extensions import is_typeddict

import hyperbrowser.models as legacy_models
import hyperbrowser.types as request_types


ACTION_TYPES = {
    "ClickActionParams",
    "DragActionParams",
    "GetClipboardTextActionParams",
    "HoldKeyActionParams",
    "ListWindowsActionParams",
    "MouseDownActionParams",
    "MouseUpActionParams",
    "MoveMouseActionParams",
    "PressKeysActionParams",
    "PutSelectionTextActionParams",
    "ScreenshotActionParams",
    "ScrollActionParams",
    "TypeTextActionParams",
}

# These public methods intentionally accept hydrated response/resource objects rather
# than request payloads. Every other Pydantic model in a public parameter annotation
# must have, and be paired with, a same-named request TypedDict.
NON_REQUEST_MODEL_INPUTS = {
    legacy_models.SandboxDetail,
    legacy_models.SessionDetail,
}


def _annotation_members(annotation, *, traverse_typed_dicts=False):
    members = set()
    pending = [annotation]
    while pending:
        member = pending.pop()
        try:
            if member in members:
                continue
            members.add(member)
        except TypeError:
            continue
        pending.extend(get_args(member))
        if traverse_typed_dicts and is_typeddict(member):
            pending.extend(get_type_hints(member).values())
    return members


def _legacy_field_name(name: str) -> str:
    return "schema" if name == "schema_" else name


def _is_typed_request(annotation) -> bool:
    variants = get_args(annotation)
    return is_typeddict(annotation) or (
        bool(variants) and all(is_typeddict(variant) for variant in variants)
    )


def test_typed_request_models_track_legacy_request_fields_and_required_keys():
    compared = 0
    for name in request_types.__all__:
        request_type = getattr(request_types, name)
        legacy_model = getattr(legacy_models, name, None)
        if (
            not is_typeddict(request_type)
            or not inspect.isclass(legacy_model)
            or not issubclass(legacy_model, BaseModel)
            or name == "StartSandboxFromSnapshotParams"
        ):
            continue

        request_fields = set(request_type.__annotations__)
        legacy_fields = {
            _legacy_field_name(field_name) for field_name in legacy_model.model_fields
        }
        assert request_fields == legacy_fields, name

        request_required = set(request_type.__required_keys__)
        legacy_required = {
            _legacy_field_name(field_name)
            for field_name, field in legacy_model.model_fields.items()
            if field.is_required()
        }
        if name in ACTION_TYPES:
            legacy_required.add("action")
        assert request_required == legacy_required, name
        compared += 1

    assert compared >= 100


def test_sandbox_create_types_express_the_valid_launch_source_shapes():
    variants = set(get_args(request_types.CreateSandboxParams))

    assert variants == {
        request_types.CreateSandboxFromImageParams,
        request_types.CreateSandboxFromSnapshotParams,
    }
    assert request_types.CreateSandboxFromImageParams.__required_keys__ == {
        "image_name"
    }
    assert request_types.CreateSandboxFromSnapshotParams.__required_keys__ == {
        "snapshot_name"
    }
    assert request_types.StartSandboxFromSnapshotParams is (
        request_types.CreateSandboxFromSnapshotParams
    )


def test_request_annotations_do_not_leak_pydantic_models():
    leaked = []
    for name in request_types.__all__:
        request_type = getattr(request_types, name)
        if not is_typeddict(request_type):
            continue
        for member in _annotation_members(
            request_type,
            traverse_typed_dicts=True,
        ):
            if inspect.isclass(member) and issubclass(member, BaseModel):
                leaked.append(f"{name}: {member.__module__}.{member.__name__}")

    assert leaked == []


def test_every_public_request_model_input_has_and_accepts_a_typed_dict():
    managers_root = Path(__file__).parents[1] / "hyperbrowser" / "client" / "managers"
    checked = 0
    checked_typed = 0
    seen_non_request_models = set()

    for path in managers_root.rglob("*.py"):
        if path.name == "__init__.py" and path.parent.name not in {"agents", "web"}:
            continue
        module_name = ".".join(
            path.with_suffix("").relative_to(Path(__file__).parents[1]).parts
        )
        if path.name == "__init__.py":
            module_name = ".".join(
                path.parent.relative_to(Path(__file__).parents[1]).parts
            )
        module = importlib.import_module(module_name)

        for _, manager in inspect.getmembers(module, inspect.isclass):
            if manager.__module__ != module.__name__:
                continue
            for method_name, method in inspect.getmembers(manager, inspect.isfunction):
                if method_name.startswith("_"):
                    continue
                hints = get_type_hints(method)
                for parameter_name in inspect.signature(method).parameters:
                    if parameter_name in {"self", "cls"} or parameter_name not in hints:
                        continue
                    annotation_members = _annotation_members(hints[parameter_name])
                    typed_request_inputs = {
                        member for member in annotation_members if is_typeddict(member)
                    }
                    public_model_inputs = {
                        member
                        for member in annotation_members
                        if inspect.isclass(member) and issubclass(member, BaseModel)
                    }
                    seen_non_request_models.update(
                        public_model_inputs & NON_REQUEST_MODEL_INPUTS
                    )
                    legacy_request_models = (
                        public_model_inputs - NON_REQUEST_MODEL_INPUTS
                    )
                    for legacy_model in legacy_request_models:
                        typed_request = getattr(
                            request_types, legacy_model.__name__, None
                        )
                        assert _is_typed_request(typed_request), (
                            f"{module.__name__}.{manager.__name__}.{method_name}"
                            f" parameter {parameter_name} accepts request model "
                            f"{legacy_model.__name__}, but hyperbrowser.types has no "
                            "same-named TypedDict counterpart"
                        )
                        typed_variants = (
                            set(get_args(typed_request))
                            if not is_typeddict(typed_request)
                            else {typed_request}
                        )
                        assert typed_variants <= annotation_members, (
                            f"{module.__name__}.{manager.__name__}.{method_name}"
                            f" parameter {parameter_name} accepts "
                            f"{legacy_model.__name__} without its TypedDict counterpart"
                        )
                        checked += 1

                    for typed_request in typed_request_inputs:
                        legacy_candidates = {
                            candidate
                            for candidate in (
                                getattr(
                                    legacy_models,
                                    typed_request.__name__,
                                    None,
                                ),
                            )
                            if inspect.isclass(candidate)
                            and issubclass(candidate, BaseModel)
                        }
                        if (
                            typed_request
                            is request_types.CreateSandboxFromSnapshotParams
                        ):
                            legacy_candidates.update(
                                {
                                    legacy_models.CreateSandboxParams,
                                    legacy_models.StartSandboxFromSnapshotParams,
                                }
                            )
                        elif (
                            typed_request is request_types.CreateSandboxFromImageParams
                        ):
                            legacy_candidates.add(legacy_models.CreateSandboxParams)

                        if not legacy_candidates:
                            continue
                        assert legacy_candidates & annotation_members, (
                            f"{module.__name__}.{manager.__name__}.{method_name}"
                            f" parameter {parameter_name} accepts TypedDict "
                            f"{typed_request.__name__} without a legacy Pydantic "
                            "request counterpart"
                        )
                        checked_typed += 1

    assert checked >= 100
    assert checked_typed >= 100
    assert seen_non_request_models == NON_REQUEST_MODEL_INPUTS


def test_responses_remain_pydantic_and_legacy_requests_remain_importable():
    assert issubclass(legacy_models.SessionDetail, BaseModel)
    assert issubclass(legacy_models.FetchResponse, BaseModel)
    assert issubclass(legacy_models.CreateSessionParams, BaseModel)
    assert is_typeddict(request_types.CreateSessionParams)
