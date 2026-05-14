import threading
import time
import logging
from typing import List, Callable, Dict, Any, Optional

from .gpu_info import GPUInfo, GPUState
from .history_buffer import HistoryBuffer
from .threshold_manager import ThresholdManager, ThresholdConfig

logger = logging.getLogger(__name__)


class GPUMonitor:
    def __init__(
        self,
        gpu_id: int = 0,
        interval_ms: int = 800,
        history_size: int = 60,
        threshold_config: ThresholdConfig | None = None,
    ):
        self.gpu_id = gpu_id
        self.interval_ms = max(200, min(5000, interval_ms))
        self._history = HistoryBuffer(maxlen=history_size)
        self._threshold = ThresholdManager(threshold_config)
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._callbacks: list[Callable] = []
        self._current_info: GPUInfo | None = None
        self._last_state: GPUState | None = None
        self._nvml_handle = None
        self._nvml = None
        self._nvml_available = False
        self._consecutive_failures = 0
        self._max_failures = 5
        self._init_nvml()

    def _import_nvml(self):
        try:
            from nvidia_ml_py import pynvml
            return pynvml
        except ImportError:
            pass
        try:
            import pynvml
            return pynvml
        except ImportError:
            pass
        return None

    def _init_nvml(self) -> None:
        try:
            pynvml = self._import_nvml()
            if pynvml is None:
                raise ImportError("No NVML library available")
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_id)
            self._nvml_handle = handle
            self._nvml = pynvml
            self._nvml_available = True
            logger.info("NVML initialized successfully")
        except Exception as e:
            logger.warning(f"NVML init failed: {e}. Falling back to nvidia-smi.")
            self._nvml_available = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def nvml_available(self) -> bool:
        return self._nvml_available

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        logger.info(f"GPU Monitor started (interval={self.interval_ms}ms)")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        try:
            if self._nvml_available and hasattr(self, '_nvml') and self._nvml:
                self._nvml.nvmlShutdown()
        except Exception:
            pass
        logger.info("GPU Monitor stopped")

    def _collect_loop(self) -> None:
        while self._running:
            try:
                info = self._collect_snapshot()
                with self._lock:
                    self._current_info = info
                    self._history.add(info)

                self._consecutive_failures = 0

                state = self._threshold.evaluate(info)
                if state != self._last_state:
                    self._last_state = state
                    info.state = state
                    for cb in self._callbacks:
                        try:
                            cb(info, state)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
            except Exception as e:
                self._consecutive_failures += 1
                logger.error(f"Collection error ({self._consecutive_failures}/{self._max_failures}): {e}")

                if self._consecutive_failures >= self._max_failures:
                    logger.warning("Too many failures, attempting NVML reconnect...")
                    self._recover_nvml()
                    self._consecutive_failures = 0

            time.sleep(self.interval_ms / 1000.0)

    def _recover_nvml(self) -> None:
        """Attempt to reinitialize NVML after failures (e.g. sleep resume)."""
        try:
            if self._nvml_available and self._nvml:
                try:
                    self._nvml.nvmlShutdown()
                except Exception:
                    pass
        except Exception:
            pass
        self._nvml_available = False
        self._init_nvml()
        if self._nvml_available:
            logger.info("NVML recovered successfully")
        else:
            logger.warning("NVML recovery failed, will keep trying")

    def _collect_snapshot(self) -> GPUInfo:
        if self._nvml_available:
            return self._collect_nvml()
        return self._collect_smi()

    def _collect_nvml(self) -> GPUInfo:
        nvml = self._nvml
        handle = self._nvml_handle
        now = time.time()

        util = nvml.nvmlDeviceGetUtilizationRates(handle)
        mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
        mem_used_mb = mem_info.used / 1024.0 / 1024.0
        mem_total_mb = mem_info.total / 1024.0 / 1024.0
        mem_util = (mem_info.used / mem_info.total) * 100.0

        try:
            temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
        except Exception:
            temp = 0.0

        try:
            power_mw = nvml.nvmlDeviceGetPowerUsage(handle)
            power_draw = power_mw / 1000.0
        except Exception:
            power_draw = 0.0

        try:
            power_limit_mw = nvml.nvmlDeviceGetPowerManagementLimit(handle)
            power_limit = power_limit_mw / 1000.0
        except Exception:
            power_limit = 0.0
        # Fallback: try enforced power limit
        if power_limit == 0.0:
            try:
                power_limit_mw = nvml.nvmlDeviceGetEnforcedPowerLimit(handle)
                power_limit = power_limit_mw / 1000.0
            except Exception:
                pass

        try:
            fan_speed = float(nvml.nvmlDeviceGetFanSpeed(handle))
        except Exception:
            fan_speed = 0.0

        try:
            clock_sm = nvml.nvmlDeviceGetClockInfo(handle, nvml.NVML_CLOCK_SM)
            clock_mem = nvml.nvmlDeviceGetClockInfo(handle, nvml.NVML_CLOCK_MEM)
        except Exception:
            clock_sm = 0
            clock_mem = 0

        try:
            clock_sm_max = nvml.nvmlDeviceGetMaxClockInfo(handle, nvml.NVML_CLOCK_SM)
        except Exception:
            clock_sm_max = 3000

        try:
            name_bytes = nvml.nvmlDeviceGetName(handle)
            name = name_bytes.decode("utf-8") if isinstance(name_bytes, bytes) else name_bytes
        except Exception:
            name = "NVIDIA GPU"

        return GPUInfo(
            gpu_id=self.gpu_id,
            name=name,
            gpu_utilization=float(util.gpu),
            memory_used=mem_used_mb,
            memory_total=mem_total_mb,
            memory_utilization=round(mem_util, 1),
            temperature=float(temp),
            power_draw=power_draw,
            power_limit=power_limit,
            fan_speed=fan_speed,
            clock_sm=clock_sm,
            clock_memory=clock_mem,
            clock_sm_max=clock_sm_max,
            timestamp=now,
        )

    def _collect_smi(self) -> GPUInfo:
        import subprocess

        now = time.time()
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--id={self.gpu_id}",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit,fan.speed,clocks.sm,clocks.mem",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError(f"nvidia-smi failed: {result.stderr}")

            parts = [p.strip() for p in result.stdout.strip().split(",")]
            return GPUInfo(
                gpu_id=self.gpu_id,
                name=parts[0] if len(parts) > 0 else "NVIDIA GPU",
                gpu_utilization=float(parts[1]) if len(parts) > 1 else 0.0,
                memory_used=float(parts[2]) if len(parts) > 2 else 0.0,
                memory_total=float(parts[3]) if len(parts) > 3 else 0.0,
                memory_utilization=(float(parts[2]) / float(parts[3]) * 100.0) if len(parts) > 3 and float(parts[3]) > 0 else 0.0,
                temperature=float(parts[4]) if len(parts) > 4 else 0.0,
                power_draw=float(parts[5]) if len(parts) > 5 and parts[5] else 0.0,
                power_limit=float(parts[6]) if len(parts) > 6 and parts[6] else 0.0,
                fan_speed=float(parts[7].replace("%", "")) if len(parts) > 7 and parts[7] else 0.0,
                clock_sm=int(parts[8]) if len(parts) > 8 and parts[8] else 0,
                clock_memory=int(parts[9]) if len(parts) > 9 and parts[9] else 0,
                timestamp=now,
            )
        except Exception as e:
            logger.error(f"SMI collection error: {e}")
            return GPUInfo(gpu_id=self.gpu_id, timestamp=now)

    def get_current(self) -> GPUInfo:
        with self._lock:
            return self._current_info or GPUInfo(gpu_id=self.gpu_id)

    def get_history(self, count: int | None = None) -> List[GPUInfo]:
        with self._lock:
            return self._history.get_recent(count) if count else self._history.get_all()

    def on_state_change(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def set_interval(self, interval_ms: int) -> None:
        self.interval_ms = max(200, min(5000, interval_ms))

    def get_available_gpus(self) -> List[Dict[str, Any]]:
        gpus = []
        if self._nvml_available:
            try:
                nvml = self._nvml
                count = nvml.nvmlDeviceGetCount()
                for i in range(count):
                    handle = nvml.nvmlDeviceGetHandleByIndex(i)
                    name_bytes = nvml.nvmlDeviceGetName(handle)
                    name = name_bytes.decode("utf-8") if isinstance(name_bytes, bytes) else name_bytes
                    gpus.append({"id": i, "name": name})
            except Exception:
                pass

        if not gpus:
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=index,name", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5,
                )
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = [p.strip() for p in line.split(",", 1)]
                        gpus.append({"id": int(parts[0]), "name": parts[1]})
            except Exception:
                pass

        return gpus

    def set_gpu(self, gpu_id: int) -> bool:
        was_running = self._running
        if was_running:
            self.stop()
        self.gpu_id = gpu_id
        self._init_nvml()
        self._history.clear()
        self._last_state = None
        if was_running:
            self.start()
        return self._nvml_available

    def update_thresholds(self, config: ThresholdConfig | Dict[str, Any]) -> None:
        if isinstance(config, dict):
            self._threshold.update(config)
        else:
            self._threshold.config = config
