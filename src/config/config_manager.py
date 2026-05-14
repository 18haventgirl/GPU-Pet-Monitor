import json
import os
import logging
from pathlib import Path
from typing import Dict, Any

from .settings import AppSettings
from ..platform.factory import get_platform_utils

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "gpu_id": 0,
    "interval_ms": 800,
    "window_scale": 1.0,
    "window_opacity": 0.95,
    "panel_visible": True,
    "window_x": 100,
    "window_y": 100,
    "click_through_enabled": False,
    "autostart_enabled": False,
    "display_items": ["gpu_util", "vram", "temp", "power", "fan", "clock", "mini_chart"],
    "notification_enabled": True,
    "sound_enabled": True,
    "skin_id": "default_cat",
    "thresholds": {
        "gpu_warn": 60.0, "gpu_critical": 85.0,
        "memory_warn": 60.0, "memory_critical": 85.0,
        "temp_warn": 70.0, "temp_critical": 85.0,
        "power_warn": 70.0, "power_critical": 90.0,
    },
    "theme": {
        "normal_color": "#4CAF50",
        "warning_color": "#FF9800",
        "critical_color": "#F44336",
        "text_color": "#FFFFFF",
        "panel_bg": "rgba(30, 30, 40, 0.75)",
    },
}


class ConfigManager:
    def __init__(self):
        self._platform = get_platform_utils()
        self._config_dir = Path(self._platform.get_config_path())
        self._config_file = self._config_dir / "config.json"
        self._settings: AppSettings = AppSettings()
        self.load()

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def load(self) -> None:
        try:
            if self._config_file.exists():
                data = json.loads(self._config_file.read_text(encoding="utf-8"))
                merged = {**DEFAULT_CONFIG, **data}
                self._apply_dict(merged)
                logger.info(f"Config loaded from {self._config_file}")
            else:
                self._apply_dict(DEFAULT_CONFIG)
                self.save()
                logger.info("Default config created")
        except Exception as e:
            logger.error(f"Config load failed: {e}, using defaults")
            self._apply_dict(DEFAULT_CONFIG)

    def save(self) -> None:
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            data = self._to_dict()
            self._config_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Config save failed: {e}")

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        s = self._settings
        s.gpu_id = data.get("gpu_id", s.gpu_id)
        s.interval_ms = data.get("interval_ms", s.interval_ms)
        s.window_scale = data.get("window_scale", s.window_scale)
        s.window_opacity = data.get("window_opacity", s.window_opacity)
        s.panel_visible = data.get("panel_visible", s.panel_visible)
        s.window_x = data.get("window_x", s.window_x)
        s.window_y = data.get("window_y", s.window_y)
        s.click_through_enabled = data.get("click_through_enabled", s.click_through_enabled)
        s.autostart_enabled = data.get("autostart_enabled", s.autostart_enabled)
        s.display_items = data.get("display_items", s.display_items)
        s.notification_enabled = data.get("notification_enabled", s.notification_enabled)
        s.sound_enabled = data.get("sound_enabled", s.sound_enabled)
        s.skin_id = data.get("skin_id", s.skin_id)
        s.thresholds = data.get("thresholds", s.thresholds)
        s.theme = data.get("theme", s.theme)

    def _to_dict(self) -> Dict[str, Any]:
        s = self._settings
        return {
            "gpu_id": s.gpu_id,
            "interval_ms": s.interval_ms,
            "window_scale": s.window_scale,
            "window_opacity": s.window_opacity,
            "panel_visible": s.panel_visible,
            "window_x": s.window_x,
            "window_y": s.window_y,
            "click_through_enabled": s.click_through_enabled,
            "autostart_enabled": s.autostart_enabled,
            "display_items": s.display_items,
            "notification_enabled": s.notification_enabled,
            "sound_enabled": s.sound_enabled,
            "skin_id": s.skin_id,
            "thresholds": s.thresholds,
            "theme": s.theme,
        }
