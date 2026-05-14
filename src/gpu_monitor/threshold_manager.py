from dataclasses import dataclass
from typing import Dict, Any

from .gpu_info import GPUInfo, GPUState


@dataclass
class ThresholdConfig:
    gpu_warn: float = 60.0
    gpu_critical: float = 85.0
    memory_warn: float = 60.0
    memory_critical: float = 85.0
    temp_warn: float = 70.0
    temp_critical: float = 85.0
    power_warn: float = 70.0
    power_critical: float = 90.0


_THRESHOLD_RULES = [
    ("gpu_utilization", "gpu_warn", "gpu_critical"),
    ("memory_utilization", "memory_warn", "memory_critical"),
    ("temperature", "temp_warn", "temp_critical"),
]


class ThresholdManager:
    def __init__(self, config: ThresholdConfig | None = None):
        self.config = config or ThresholdConfig()

    def evaluate(self, info: GPUInfo) -> GPUState:
        worst = GPUState.NORMAL

        for field, warn_key, crit_key in _THRESHOLD_RULES:
            value = getattr(info, field, 0.0)
            warn_val = getattr(self.config, warn_key)
            crit_val = getattr(self.config, crit_key)

            if value >= crit_val:
                return GPUState.CRITICAL
            if value >= warn_val and worst.value < GPUState.WARNING.value:
                worst = GPUState.WARNING

        if info.gpu_utilization < 10.0:
            if worst == GPUState.NORMAL:
                return GPUState.IDLE
        elif 10.0 <= info.gpu_utilization < 30.0:
            pass
        else:
            if worst == GPUState.NORMAL:
                return GPUState.WORKING

        return worst

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gpu_warn": self.config.gpu_warn,
            "gpu_critical": self.config.gpu_critical,
            "memory_warn": self.config.memory_warn,
            "memory_critical": self.config.memory_critical,
            "temp_warn": self.config.temp_warn,
            "temp_critical": self.config.temp_critical,
            "power_warn": self.config.power_warn,
            "power_critical": self.config.power_critical,
        }

    def update(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            if hasattr(self.config, key):
                setattr(self.config, key, float(value))
