from urllib.parse import urlsplit, urlunsplit

import httpx

from tests.helpers.config import API_KEY, BASE_URL, REGIONAL_PROXY_DEV_HOST


def _has_scheme(value: str) -> bool:
    return "://" in value


def _resolve_signed_url_target(input_url: str):
    original = urlsplit(input_url)
    if not REGIONAL_PROXY_DEV_HOST:
        return input_url, None

    override = urlsplit(
        REGIONAL_PROXY_DEV_HOST
        if _has_scheme(REGIONAL_PROXY_DEV_HOST)
        else f"{original.scheme}://{REGIONAL_PROXY_DEV_HOST}"
    )
    rewritten = urlunsplit(
        (
            override.scheme or original.scheme,
            override.netloc or original.netloc,
            original.path,
            original.query,
            original.fragment,
        )
    )
    return rewritten, original.netloc


def fetch_signed_url(
    input_url: str,
    *,
    method: str = "GET",
    body=None,
    headers=None,
) -> httpx.Response:
    url, host_header = _resolve_signed_url_target(input_url)
    request_headers = dict(headers or {})
    if host_header and "Host" not in request_headers and "host" not in request_headers:
        request_headers["Host"] = host_header
    return httpx.request(method, url, headers=request_headers, content=body, timeout=30)


def fetch_runtime_url(
    input_url: str,
    *,
    method: str = "GET",
    body=None,
    headers=None,
) -> httpx.Response:
    return fetch_signed_url(
        input_url,
        method=method,
        body=body,
        headers=headers,
    )


def get_image_by_name(image_name: str):
    response = httpx.get(
        f"{BASE_URL}/api/images",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    images = payload.get("data", {}).get("images") or payload.get("images") or []
    image = next(
        (entry for entry in images if entry.get("imageName") == image_name), None
    )
    if image is None:
        raise RuntimeError(f"custom image {image_name!r} not found in /api/images")
    return image


async def get_image_by_name_async(image_name: str):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{BASE_URL}/api/images",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    response.raise_for_status()
    payload = response.json()
    images = payload.get("data", {}).get("images") or payload.get("images") or []
    image = next(
        (entry for entry in images if entry.get("imageName") == image_name), None
    )
    if image is None:
        raise RuntimeError(f"custom image {image_name!r} not found in /api/images")
    return image
