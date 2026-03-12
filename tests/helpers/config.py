import os
from pathlib import Path

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser

TESTS_DIR = Path(__file__).resolve().parent.parent
ENV_PATHS = (
    TESTS_DIR / ".env",
    TESTS_DIR.parent / ".env",
)


def _load_env() -> None:
    for env_path in ENV_PATHS:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        return


_load_env()

API_KEY = os.environ.get("HYPERBROWSER_API_KEY", "")
BASE_URL = os.environ.get("HYPERBROWSER_BASE_URL", "http://localhost:8080")
REGIONAL_PROXY_DEV_HOST = os.environ.get("REGIONAL_PROXY_DEV_HOST", "")
DEFAULT_IMAGE_NAME = os.environ.get("HYPERBROWSER_DEFAULT_IMAGE_NAME", "node")


def create_client() -> Hyperbrowser:
    if not API_KEY:
        raise RuntimeError(
            "Set HYPERBROWSER_API_KEY in tests/.env before running sandbox e2e tests"
        )

    return Hyperbrowser(
        api_key=API_KEY,
        base_url=BASE_URL,
        runtime_proxy_override=REGIONAL_PROXY_DEV_HOST or None,
    )


def create_async_client() -> AsyncHyperbrowser:
    if not API_KEY:
        raise RuntimeError(
            "Set HYPERBROWSER_API_KEY in tests/.env before running sandbox e2e tests"
        )

    return AsyncHyperbrowser(
        api_key=API_KEY,
        base_url=BASE_URL,
        runtime_proxy_override=REGIONAL_PROXY_DEV_HOST or None,
    )


def make_test_name(prefix: str) -> str:
    import random
    import time

    return f"{prefix}-{int(time.time() * 1000)}-{random.randrange(16**6):06x}"
