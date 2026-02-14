from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_web_pagination_utils_reuses_job_pagination_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/web_pagination_utils.py"
    ).read_text(encoding="utf-8")
    assert "initialize_job_paginated_response(" in module_text
    assert "merge_job_paginated_page_response(" in module_text
    assert "build_job_paginated_page_merge_callback(" in module_text
    assert "totalPages" in module_text
