from collections import deque
from typing import List

from .gpu_info import GPUInfo


class HistoryBuffer:
    def __init__(self, maxlen: int = 60):
        self._buffer: deque[GPUInfo] = deque(maxlen=maxlen)
        self._maxlen = maxlen

    def add(self, info: GPUInfo) -> None:
        self._buffer.append(info)

    def get_all(self) -> List[GPUInfo]:
        return list(self._buffer)

    def get_recent(self, count: int) -> List[GPUInfo]:
        items = list(self._buffer)
        return items[-count:] if count > 0 else []

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)

    def __getitem__(self, index: int) -> GPUInfo:
        return self._buffer[index]
