import os
from pathlib import Path

from hyperbrowser import Hyperbrowser

TESTS_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = TESTS_DIR / ".env"


def _load_env() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

API_KEY = os.environ.get("HYPERBROWSER_API_KEY", "")
BASE_URL = os.environ.get("HYPERBROWSER_BASE_URL", "http://localhost:8080")
REGIONAL_PROXY_DEV_HOST = os.environ.get("REGIONAL_PROXY_DEV_HOST", "")
DEFAULT_SNAPSHOT_NAME = "receiverStarted-ubuntu-24-node"


def create_client() -> Hyperbrowser:
    if not API_KEY:
        raise RuntimeError(
            "Set HYPERBROWSER_API_KEY in tests/.env before running sandbox e2e tests"
        )

    return Hyperbrowser(api_key=API_KEY, base_url=BASE_URL)


def make_test_name(prefix: str) -> str:
    import random
    import time

    return f"{prefix}-{int(time.time() * 1000)}-{random.randrange(16**6):06x}"
