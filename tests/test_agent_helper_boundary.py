from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


AGENT_MANAGER_DIRS = (
    Path("hyperbrowser/client/managers/sync_manager/agents"),
    Path("hyperbrowser/client/managers/async_manager/agents"),
)


def test_agent_managers_use_shared_helper_boundaries():
    violating_modules: list[str] = []
    for base_dir in AGENT_MANAGER_DIRS:
        for module_path in sorted(base_dir.glob("*.py")):
            if module_path.name == "__init__.py":
                continue
            module_text = module_path.read_text(encoding="utf-8")
            if (
                "_client.transport.get(" in module_text
                or "_client.transport.post(" in module_text
                or "_client.transport.put(" in module_text
                or "parse_response_model(" in module_text
            ):
                violating_modules.append(module_path.as_posix())

    assert violating_modules == []
