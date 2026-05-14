import os
import sys
import ctypes
from ctypes import wintypes
from pathlib import Path

from .base import PlatformUtils

_USER32 = ctypes.windll.user32

WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
GWL_EXSTYLE = -20
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010


class WindowsUtils(PlatformUtils):
    def set_window_always_on_top(self, hwnd: int, enable: bool = True) -> None:
        if enable:
            _USER32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        else:
            _USER32.SetWindowPos(hwnd, -2, 0, 0, 0, 0,
                                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    def set_window_click_through(self, hwnd: int, enable: bool) -> None:
        style = _USER32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        _USER32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def set_autostart(self, enable: bool) -> None:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        if enable:
            exe_path = sys.executable
            script_path = os.path.abspath(sys.argv[0]) if sys.argv else exe_path
            winreg.SetValueEx(key, "GPUPetMonitor", 0, winreg.REG_SZ, f'"{exe_path}" "{script_path}"')
        else:
            try:
                winreg.DeleteValue(key, "GPUPetMonitor")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)

    def get_autostart_status(self) -> bool:
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ,
            )
            try:
                winreg.QueryValueEx(key, "GPUPetMonitor")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    def show_notification(self, title: str, message: str, icon: str = "info") -> None:
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title, message, duration=5)
        except ImportError:
            import subprocess
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("GPU Pet Monitor").Show($toast)
            '''
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

    def get_config_path(self) -> str:
        appdata = os.environ.get("APPDATA", str(Path.home()))
        path = os.path.join(appdata, "GPUPetMonitor")
        os.makedirs(path, exist_ok=True)
        return path

    def get_system_info(self) -> dict:
        return {
            "platform": sys.platform,
            "os": "Windows",
            "version": sys.getwindowsversion().major if hasattr(sys, 'getwindowsversion') else None,
        }
