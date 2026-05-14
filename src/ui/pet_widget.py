from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QElapsedTimer
from PyQt5.QtGui import QPainter, QColor

from ..animation.animation_state_machine import AnimationStateMachine, AnimationState
from ..animation.procedural_animator import ProceduralAnimator
from ..skins.skin_manager import SkinManager, SkinMeta

GPU_TO_ANIM = {
    "idle": AnimationState.IDLE,
    "normal": AnimationState.NORMAL,
    "working": AnimationState.WORKING,
    "warning": AnimationState.WARNING,
    "critical": AnimationState.CRITICAL,
    "error": AnimationState.NORMAL,
    "no_gpu": AnimationState.SLEEPING,
}

ANIM_BUBBLE_TEXT = {
    AnimationState.IDLE: "zzZ... GPU在休息~",
    AnimationState.NORMAL: "状态良好~",
    AnimationState.WORKING: "正在工作中!",
    AnimationState.WARNING: "有点热了... 注意!",
    AnimationState.CRITICAL: "太热了!!! 快关程序!",
    AnimationState.SLEEPING: "Zzz... 好安静...",
    AnimationState.GREETING: "你好呀!",
    AnimationState.HOVER: "嗯?",
}


class PetWidget(QWidget):
    def __init__(self, parent=None, size: int = 195):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size + 30)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)  # Enable hover tracking

        self._state_machine = AnimationStateMachine()
        self._animator = ProceduralAnimator()
        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_elapsed: float = 0.0
        self._last_state: AnimationState = AnimationState.IDLE
        self._visible: bool = True

        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._tick)
        self._set_fps(30)  # Default 30fps, bump on activity

    def _set_fps(self, fps: int):
        interval = 1000 // max(1, fps)
        if self._render_timer.interval() != interval:
            self._render_timer.start(interval)

    def _tick(self):
        if not self._visible:
            return

        elapsed = self._clock.elapsed() / 1000.0
        dt = elapsed - self._last_elapsed
        self._last_elapsed = elapsed
        dt = min(dt, 0.1)

        result = self._state_machine.update(dt)
        if result:
            self._animator.set_state(result)

        self._animator.update(dt)

        # Adaptive FPS: 60fps during transitions/hover/warning+, else 30fps
        current = self._state_machine.current
        if (self._animator._is_transitioning or self._animator._hover_active
                or current in (AnimationState.WARNING, AnimationState.CRITICAL,
                               AnimationState.WORKING)):
            self._set_fps(60)
        else:
            self._set_fps(30)

        self.update()

    def set_character(self, char_type: str):
        self._animator.set_character(char_type)

    def set_gpu_state(self, state_str: str) -> None:
        anim_state = GPU_TO_ANIM.get(state_str, AnimationState.NORMAL)
        text = ANIM_BUBBLE_TEXT.get(anim_state, "")

        if self._state_machine.current == anim_state:
            self._animator.set_state(anim_state, custom_text=text)
            return

        self._state_machine.request_state(anim_state, transition_ms=400)
        self._animator.set_state(anim_state, transition_ms=400, custom_text=text)

    # ── Mouse hover + drag forwarding ────────────────────
    def enterEvent(self, event):
        self._animator.set_mouse(event.x(), event.y(), True)

    def leaveEvent(self, event):
        self._animator.set_mouse(0, 0, False)

    def mousePressEvent(self, event):
        self._animator.set_mouse(event.x(), event.y(), True)
        # Forward to FloatingWindow for drag
        win = self.window()
        if win and hasattr(win, 'mousePressEvent'):
            win.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._animator.set_mouse(event.x(), event.y(), True)
        win = self.window()
        if win and hasattr(win, 'mouseMoveEvent'):
            win.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        win = self.window()
        if win and hasattr(win, 'mouseReleaseEvent'):
            win.mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        win = self.window()
        if win and hasattr(win, 'mouseDoubleClickEvent'):
            win.mouseDoubleClickEvent(event)

    # ── Visibility (performance) ─────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        self._visible = True

    def hideEvent(self, event):
        super().hideEvent(event)
        self._visible = False

    def paintEvent(self, event):
        painter = QPainter(self)
        self._animator.render(painter, self._size, self._size + 25)

    @property
    def current_state(self) -> AnimationState:
        return self._state_machine.current
