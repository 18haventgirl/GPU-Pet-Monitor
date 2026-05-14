from dataclasses import dataclass, field
from typing import List


@dataclass
class AppSettings:
    gpu_id: int = 0
    interval_ms: int = 800
    window_scale: float = 1.0
    window_opacity: float = 0.95
    panel_visible: bool = True
    window_x: int = 100
    window_y: int = 100
    click_through_enabled: bool = False
    autostart_enabled: bool = False

    display_items: List[str] = field(default_factory=lambda: [
        "gpu_util", "vram", "temp", "power", "fan", "clock", "mini_chart",
    ])
    notification_enabled: bool = True
    sound_enabled: bool = True

    skin_id: str = "default_cat"

    thresholds: dict = field(default_factory=lambda: {
        "gpu_warn": 60.0, "gpu_critical": 85.0,
        "memory_warn": 60.0, "memory_critical": 85.0,
        "temp_warn": 70.0, "temp_critical": 85.0,
        "power_warn": 70.0, "power_critical": 90.0,
    })

    theme: dict = field(default_factory=lambda: {
        "normal_color": "#4CAF50",
        "warning_color": "#FF9800",
        "critical_color": "#F44336",
        "text_color": "#FFFFFF",
        "panel_bg": "rgba(30, 30, 40, 0.75)",
    })
