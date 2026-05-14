import sys
import time
from typing import Optional

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from .gpu_monitor.collector import GPUMonitor
from .gpu_monitor.demo_mode import DemoMonitor
from .gpu_monitor.gpu_info import GPUState
from .gpu_monitor.threshold_manager import ThresholdConfig
from .config.config_manager import ConfigManager
from .skins.skin_manager import SkinManager
from .ui.main_window import FloatingWindow
from .ui.tray_icon import TrayIcon
from .ui.settings_window import SettingsWindow
from .utils.logger import setup_logger

logger = setup_logger("gpupet")

NOTIFY_COOLDOWN_S = 30  # Minimum seconds between repeated notifications


class GPUPetApp:
    def __init__(self):
        self._config = ConfigManager()
        self._skin_manager = SkinManager()
        self._skin_manager.scan()
        self._skin_manager.activate(self._config.settings.skin_id)

        self._qt_app = QApplication(sys.argv)
        self._qt_app.setQuitOnLastWindowClosed(False)

        font = self._qt_app.font()
        font.setPointSize(10)
        self._qt_app.setFont(font)

        self._window: Optional[FloatingWindow] = None
        self._tray: Optional[TrayIcon] = None
        self._monitor = None
        self._timer: Optional[QTimer] = None
        self._use_demo = False
        self._last_notify: float = 0.0
        self._last_state: GPUState | None = None
        self._tick_count: int = 0

    def run(self):
        self._window = FloatingWindow(self._config)
        self._tray = TrayIcon(self)

        self._init_monitor()
        self._setup_timer()

        # Apply initial display items + skin
        self._window.set_display_items(self._config.settings.display_items)
        skin = self._skin_manager.active_skin
        if skin:
            self._window.apply_skin(skin.character_type)

        self._tray.show()
        self._window.show()
        logger.info("GPU Pet Monitor started")

        try:
            self._qt_app.exec_()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.exception(f"Application error: {e}")
        finally:
            self._shutdown()

    def _init_monitor(self):
        s = self._config.settings
        t = s.thresholds

        threshold_config = ThresholdConfig(
            gpu_warn=t.get("gpu_warn", 60.0),
            gpu_critical=t.get("gpu_critical", 85.0),
            memory_warn=t.get("memory_warn", 60.0),
            memory_critical=t.get("memory_critical", 85.0),
            temp_warn=t.get("temp_warn", 70.0),
            temp_critical=t.get("temp_critical", 85.0),
            power_warn=t.get("power_warn", 70.0),
            power_critical=t.get("power_critical", 90.0),
        )

        self._use_demo = False
        try:
            self._monitor = GPUMonitor(
                gpu_id=s.gpu_id,
                interval_ms=s.interval_ms,
                threshold_config=threshold_config,
            )
            if not self._monitor.nvml_available:
                logger.warning("NVML not available, trying nvidia-smi...")
        except Exception as e:
            logger.error(f"GPU monitor init failed: {e}")

        if self._monitor is None or not self._monitor.nvml_available:
            logger.warning("Starting in Demo mode")
            self._use_demo = True
            self._monitor = DemoMonitor(
                gpu_id=s.gpu_id,
                interval_ms=s.interval_ms,
            )

        self._monitor.on_state_change(self._on_state_change)
        self._monitor.start()
        self._window.set_use_demo(self._use_demo)

    def _setup_timer(self):
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._config.settings.interval_ms)

    def _tick(self):
        try:
            info = self._monitor.get_current()
            if info is None:
                return

            state_str = self._window.update_gpu_info(info)
            if self._tray:
                self._tray.set_state_icon(state_str)
        except Exception as e:
            logger.error(f"Tick error: {e}")

    def _on_state_change(self, info, new_state: GPUState):
        logger.info(f"GPU state changed to: {new_state.value}")

        s = self._config.settings
        if not s.notification_enabled:
            return

        if new_state == GPUState.CRITICAL:
            now = time.time()
            if now - self._last_notify > NOTIFY_COOLDOWN_S:
                self._last_notify = now
                self._send_notification(
                    "GPU 危险警告!",
                    f"温度: {info.temperature:.0f}°C | "
                    f"使用率: {info.gpu_utilization:.0f}% | "
                    f"显存: {info.memory_utilization:.0f}%"
                )
        elif new_state == GPUState.WARNING:
            now = time.time()
            if now - self._last_notify > NOTIFY_COOLDOWN_S * 2:
                self._last_notify = now
                self._send_notification(
                    "GPU 需要注意",
                    f"温度: {info.temperature:.0f}°C | "
                    f"使用率: {info.gpu_utilization:.0f}%"
                )

    def _send_notification(self, title: str, message: str):
        try:
            from .platform.factory import get_platform_utils
            get_platform_utils().show_notification(title, message)
        except Exception as e:
            logger.debug(f"Notification failed (non-critical): {e}")

    def open_settings(self):
        gpu_list = self._monitor.get_available_gpus() if self._monitor else []
        if not gpu_list:
            gpu_list = [{"id": 0, "name": "NVIDIA GPU (Demo)"}]

        dialog = SettingsWindow(
            self._config, self._skin_manager, gpu_list, parent=None
        )
        dialog.setWindowOpacity(0.95)

        if dialog.exec_() and dialog.is_modified:
            self._apply_settings()

    def _apply_settings(self):
        """Apply settings changed in the dialog."""
        s = self._config.settings

        # Window appearance
        self._window.setWindowOpacity(s.window_opacity)
        self._window.resize(
            int(435 * s.window_scale), int(260 * s.window_scale)
        )

        # Display items
        self._window.set_display_items(s.display_items)

        # Click-through
        if s.click_through_enabled:
            pass  # Enabled via timer-based mouse-idle detection (future)

        # Autostart
        from .platform.factory import get_platform_utils
        get_platform_utils().set_autostart(s.autostart_enabled)

        # Thresholds — update monitor in-place
        if self._monitor:
            self._monitor.update_thresholds(s.thresholds)

        # Interval — restart timer
        if self._timer:
            self._timer.setInterval(s.interval_ms)

        # GPU switch — reinit monitor
        old_gpu = (self._monitor.gpu_id
                   if hasattr(self._monitor, 'gpu_id') else s.gpu_id)
        if s.gpu_id != old_gpu:
            self._monitor.stop()
            self._init_monitor()

        logger.info("Settings applied")

    def toggle_visibility(self):
        if self._window.isVisible():
            self._window.hide()
        else:
            s = self._config.settings
            self._window.move(s.window_x, s.window_y)
            self._window.show()

    def restart(self):
        self._shutdown()
        import subprocess, os
        exe = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                           "GPU-Pet-Monitor.exe")
        if getattr(sys, 'frozen', False) and os.path.isfile(exe):
            subprocess.Popen([exe])
        else:
            subprocess.Popen([sys.executable] + sys.argv)
        self._qt_app.quit()

    def quit(self):
        self._shutdown()
        self._qt_app.quit()

    def _shutdown(self):
        if self._timer:
            self._timer.stop()
        if self._monitor:
            self._monitor.stop()
        self._config.save()
        logger.info("GPU Pet Monitor stopped")

    @property
    def config_manager(self):
        return self._config

    @property
    def skin_manager(self):
        return self._skin_manager

    @property
    def qt_app(self):
        return self._qt_app

    @property
    def monitor(self):
        return self._monitor

    def switch_skin(self, skin_id: str):
        if not self._skin_manager.activate(skin_id):
            logger.warning(f"Skin activate failed: {skin_id}")
            return
        self._config.settings.skin_id = skin_id
        self._config.save()

        skin = self._skin_manager.active_skin
        if skin and self._window:
            self._window.apply_skin(skin.character_type)
            logger.info(f"Skin switched to: {skin_id} ({skin.character_type})")
        else:
            logger.warning(f"Skin apply skipped: skin={skin}, window={self._window}")
