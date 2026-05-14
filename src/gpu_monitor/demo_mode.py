import random
import time
from typing import List, Dict, Any

from .gpu_info import GPUInfo, GPUState


_demo_scenarios = [
    {
        "name": "idle_desktop",
        "gpu_util": (0, 8),
        "mem_util": (15, 25),
        "temp": (35, 45),
        "power_frac": (0.05, 0.15),
        "duration": 30,
    },
    {
        "name": "browsing",
        "gpu_util": (5, 20),
        "mem_util": (20, 35),
        "temp": (40, 50),
        "power_frac": (0.10, 0.25),
        "duration": 20,
    },
    {
        "name": "video_playback",
        "gpu_util": (15, 35),
        "mem_util": (25, 45),
        "temp": (45, 60),
        "power_frac": (0.15, 0.40),
        "duration": 25,
    },
    {
        "name": "light_gaming",
        "gpu_util": (40, 70),
        "mem_util": (40, 65),
        "temp": (55, 72),
        "power_frac": (0.40, 0.70),
        "duration": 30,
    },
    {
        "name": "heavy_compute",
        "gpu_util": (70, 98),
        "mem_util": (60, 92),
        "temp": (65, 88),
        "power_frac": (0.60, 0.95),
        "duration": 20,
    },
]


class DemoMonitor:
    def __init__(self, gpu_id: int = 0, interval_ms: int = 800):
        self.gpu_id = gpu_id
        self.interval_ms = interval_ms
        self._running = False
        self._callbacks: list = []
        self._current_info: GPUInfo | None = None
        self._scenario_index = 0
        self._scenario_elapsed = 0.0
        self._prev_values: dict[str, float] = {}
        self._transitioning = False
        self._transition_remaining = 0.0
        self._transition_duration = 3.0  # 3s crossfade
        self._memory_base = 16 * 1024  # 16 GB
        self._power_limit = 320.0
        self._last_state = GPUState.NORMAL

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def _sample_scenario(self, scenario: dict) -> dict:
        return {
            "gpu_util": random.uniform(*scenario["gpu_util"]),
            "mem_util": random.uniform(*scenario["mem_util"]),
            "temp": random.uniform(*scenario["temp"]),
            "power_frac": random.uniform(*scenario["power_frac"]),
        }

    def get_current(self) -> GPUInfo:
        now = time.time()
        scenario = _demo_scenarios[self._scenario_index]

        # Advance time
        self._scenario_elapsed += self.interval_ms / 1000.0
        duration = scenario["duration"]

        # Check for scenario change
        if self._scenario_elapsed > duration:
            # Start transition
            self._prev_values = self._sample_scenario(scenario)
            self._scenario_index = (self._scenario_index + 1) % len(_demo_scenarios)
            self._scenario_elapsed = 0.0
            self._transition_remaining = self._transition_duration

        scenario = _demo_scenarios[self._scenario_index]
        current = self._sample_scenario(scenario)

        # Interpolate during transition
        if self._transition_remaining > 0:
            t = max(0, self._transition_remaining / self._transition_duration)
            for k in current:
                if k in self._prev_values:
                    current[k] = self._prev_values[k] * t + current[k] * (1 - t)
            self._transition_remaining -= self.interval_ms / 1000.0

        gpu_util = round(current["gpu_util"], 1)
        mem_util = round(current["mem_util"], 1)
        temp = round(current["temp"], 1)
        power_frac = current["power_frac"]

        mem_used = (mem_util / 100.0) * self._memory_base

        info = GPUInfo(
            gpu_id=self.gpu_id,
            name="NVIDIA GeForce RTX 4090 (Demo)",
            gpu_utilization=gpu_util,
            memory_used=mem_used,
            memory_total=self._memory_base,
            memory_utilization=mem_util,
            temperature=temp,
            power_draw=round(self._power_limit * power_frac, 1),
            power_limit=self._power_limit,
            fan_speed=round(min(100, 30 + temp * 1.2), 1),
            clock_sm=random.randint(1800, 2800),
            clock_memory=random.randint(9000, 11000),
            timestamp=now,
        )

        self._current_info = info
        return info

    def get_history(self, seconds: int = 60) -> List[GPUInfo]:
        return [self.get_current() for _ in range(min(seconds, 10))]

    def on_state_change(self, callback) -> None:
        self._callbacks.append(callback)

    def get_available_gpus(self) -> List[Dict[str, Any]]:
        return [{"id": 0, "name": "NVIDIA GeForce RTX 4090 (Demo)"}]
