from dataclasses import dataclass, field
from enum import Enum
import time


class GPUState(Enum):
    IDLE = "idle"
    NORMAL = "normal"
    WORKING = "working"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"
    NO_GPU = "no_gpu"


@dataclass
class GPUInfo:
    gpu_id: int
    name: str = "Unknown"
    gpu_utilization: float = 0.0
    memory_used: float = 0.0
    memory_total: float = 0.0
    memory_utilization: float = 0.0
    temperature: float = 0.0
    power_draw: float = 0.0
    power_limit: float = 0.0
    fan_speed: float = 0.0
    clock_sm: int = 0
    clock_memory: int = 0
    clock_sm_max: int = 3000
    timestamp: float = field(default_factory=time.time)
    state: GPUState = GPUState.NORMAL

    @property
    def memory_used_gb(self) -> float:
        return self.memory_used / 1024.0

    @property
    def memory_total_gb(self) -> float:
        return self.memory_total / 1024.0

    @property
    def power_utilization(self) -> float:
        if self.power_limit > 0:
            return (self.power_draw / self.power_limit) * 100.0
        return 0.0

    @property
    def clock_utilization(self) -> float:
        if self.clock_sm_max > 0:
            return min(100.0, (self.clock_sm / self.clock_sm_max) * 100.0)
        return 0.0
