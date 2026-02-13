from importlib.metadata import PackageNotFoundError, version

PACKAGE_NAME = "hyperbrowser"

try:
    __version__ = version(PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = "0.0.0"
