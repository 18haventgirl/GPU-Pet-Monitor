import sys

from .base import PlatformUtils

_platform_utils: PlatformUtils | None = None


def get_platform_utils() -> PlatformUtils:
    global _platform_utils
    if _platform_utils is None:
        if sys.platform == "win32":
            from .windows import WindowsUtils
            _platform_utils = WindowsUtils()
        elif sys.platform == "linux":
            from .linux import LinuxUtils
            _platform_utils = LinuxUtils()
        else:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")
    return _platform_utils
