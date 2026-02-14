from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
    "hyperbrowser/client/managers/sync_manager/profile.py",
    "hyperbrowser/client/managers/async_manager/profile.py",
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
    "hyperbrowser/client/managers/web_payload_utils.py",
)


def test_managers_use_default_serialization_helper_for_optional_query_params():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "serialize_model_dump_or_default(" in module_text
        assert "params_obj = params or " not in module_text
