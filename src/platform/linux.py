import os
import sys
import subprocess
from pathlib import Path

from .base import PlatformUtils


class LinuxUtils(PlatformUtils):
    def set_window_always_on_top(self, hwnd: int, enable: bool = True) -> None:
        try:
            action = "add" if enable else "remove"
            subprocess.run(
                ["wmctrl", "-i", "-r", str(hwnd), "-b", f"{action},above"],
                capture_output=True, timeout=2,
            )
        except Exception:
            pass

    def set_window_click_through(self, hwnd: int, enable: bool) -> None:
        try:
            if enable:
                subprocess.run(
                    ["xprop", "-id", str(hwnd), "-f", "_NET_WM_WINDOW_TYPE", "32a",
                     "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DESKTOP"],
                    capture_output=True, timeout=2,
                )
        except Exception:
            pass

    def set_autostart(self, enable: bool) -> None:
        autostart_dir = Path.home() / ".config" / "autostart"
        desktop_file = autostart_dir / "gpupetmonitor.desktop"

        if enable:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            exe_path = sys.executable
            script_path = os.path.abspath(sys.argv[0]) if sys.argv else exe_path
            content = f"""[Desktop Entry]
Type=Application
Name=GPU Pet Monitor
Comment=GPU monitoring desktop pet
Exec={exe_path} {script_path}
Terminal=false
X-GNOME-Autostart-enabled=true
"""
            desktop_file.write_text(content)
        else:
            if desktop_file.exists():
                desktop_file.unlink()

    def get_autostart_status(self) -> bool:
        desktop_file = Path.home() / ".config" / "autostart" / "gpupetmonitor.desktop"
        return desktop_file.exists()

    def show_notification(self, title: str, message: str, icon: str = "info") -> None:
        try:
            subprocess.run(
                ["notify-send", title, message, "--icon", icon, "--app-name", "GPU Pet Monitor"],
                timeout=3,
            )
        except Exception:
            pass

    def get_config_path(self) -> str:
        path = Path.home() / ".config" / "gpupetmonitor"
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def get_system_info(self) -> dict:
        return {
            "platform": sys.platform,
            "os": "Linux",
            "version": None,
        }
