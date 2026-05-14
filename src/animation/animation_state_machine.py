import enum
import time
from typing import Callable, Optional
from dataclasses import dataclass


class AnimationState(enum.Enum):
    IDLE = "idle"
    NORMAL = "normal"
    WORKING = "working"
    WARNING = "warning"
    CRITICAL = "critical"
    GREETING = "greeting"
    SLEEPING = "sleeping"
    HOVER = "hover"


STATE_PRIORITY = {
    AnimationState.CRITICAL: 10,
    AnimationState.WARNING: 8,
    AnimationState.WORKING: 6,
    AnimationState.NORMAL: 4,
    AnimationState.IDLE: 2,
    AnimationState.SLEEPING: 1,
    AnimationState.GREETING: 0,
    AnimationState.HOVER: 0,
}


@dataclass
class TransitionConfig:
    duration_ms: float = 400
    fade_out: bool = True
    fade_in: bool = True


class AnimationStateMachine:
    def __init__(self):
        self._current: AnimationState = AnimationState.IDLE
        self._previous: Optional[AnimationState] = None
        self._target: Optional[AnimationState] = None
        self._transition_start: float = 0.0
        self._transition_duration: float = 0.0
        self._is_transitioning: bool = False
        self._state_entered_at: float = time.time()
        self._idle_threshold_ms: float = 30_000  # 30s → sleeping
        self._overlay_state: Optional[AnimationState] = None
        self._transition_callbacks: list[Callable] = []

    @property
    def current(self) -> AnimationState:
        return self._current

    @property
    def previous(self) -> Optional[AnimationState]:
        return self._previous

    @property
    def is_transitioning(self) -> bool:
        return self._is_transitioning

    @property
    def transition_progress(self) -> float:
        if not self._is_transitioning or self._transition_duration == 0:
            return 1.0
        elapsed = (time.time() - self._transition_start) * 1000.0
        return min(1.0, elapsed / self._transition_duration)

    def request_state(
        self, new_state: AnimationState, transition_ms: float = 400
    ) -> bool:
        if self._is_transitioning:
            if new_state == self._target:
                return False

        if new_state == self._current:
            return False

        new_priority = STATE_PRIORITY.get(new_state, 0)
        current_priority = STATE_PRIORITY.get(self._current, 0)

        if self._is_transitioning and self._target:
            target_priority = STATE_PRIORITY.get(self._target, 0)
            if new_priority > target_priority:
                self._target = new_state
                return True
            return False

        self._previous = self._current
        self._target = new_state
        self._transition_start = time.time()
        self._transition_duration = transition_ms
        self._is_transitioning = True

        for cb in self._transition_callbacks:
            try:
                cb(self._previous, new_state, transition_ms)
            except Exception:
                pass

        return True

    def complete_transition(self) -> AnimationState:
        if not self._is_transitioning or not self._target:
            return self._current
        self._current = self._target
        self._target = None
        self._is_transitioning = False
        self._state_entered_at = time.time()
        return self._current

    def update(self, dt: float) -> Optional[AnimationState]:
        if self._is_transitioning and self.transition_progress >= 1.0:
            return self.complete_transition()

        state_duration = (time.time() - self._state_entered_at) * 1000.0
        if (
            self._current == AnimationState.IDLE
            and state_duration > self._idle_threshold_ms
            and not self._is_transitioning
        ):
            self.request_state(AnimationState.SLEEPING, transition_ms=800)
            return None

        return None

    def on_transition(self, callback: Callable) -> None:
        self._transition_callbacks.append(callback)

    def set_idle_threshold(self, ms: float) -> None:
        self._idle_threshold_ms = ms
