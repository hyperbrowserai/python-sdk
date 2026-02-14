PROFILE_ROUTE_PREFIX = "/profile"
PROFILES_ROUTE_PATH = "/profiles"


def build_profile_route(profile_id: str) -> str:
    return f"{PROFILE_ROUTE_PREFIX}/{profile_id}"
