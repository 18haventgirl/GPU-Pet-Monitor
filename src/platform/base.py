from abc import ABC, abstractmethod
from typing import Any


class PlatformUtils(ABC):
    @abstractmethod
    def set_window_always_on_top(self, hwnd: int, enable: bool = True) -> None: ...

    @abstractmethod
    def set_window_click_through(self, hwnd: int, enable: bool) -> None: ...

    @abstractmethod
    def set_autostart(self, enable: bool) -> None: ...

    @abstractmethod
    def get_autostart_status(self) -> bool: ...

    @abstractmethod
    def show_notification(self, title: str, message: str, icon: str = "info") -> None: ...

    @abstractmethod
    def get_config_path(self) -> str: ...

    @abstractmethod
    def get_system_info(self) -> dict[str, Any]: ...
