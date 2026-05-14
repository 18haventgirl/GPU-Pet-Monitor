import time, math
from typing import Optional
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient
from PyQt5.QtCore import Qt, QRect

from .animation_state_machine import AnimationState
from ..utils.fonts import sans_font, mono_font


# ── Base state colors (per-state), then each character interprets them ──
STATE_COLORS = {
    AnimationState.IDLE:     ("#7899CC", "#5A7AAA", "#A8C8F0", "#FFB4C8"),
    AnimationState.SLEEPING: ("#6E8FBF", "#5070A0", "#9EBeE6", "#F0AABE"),
    AnimationState.NORMAL:   ("#8CBE8C", "#6AA06A", "#C8F0C8", "#FFC8C8"),
    AnimationState.WORKING:  ("#DCC878", "#BEAA5A", "#FFF5C8", "#FFD2B4"),
    AnimationState.WARNING:  ("#F0A050", "#D28232", "#FFDCB4", "#FF9682"),
    AnimationState.CRITICAL: ("#F06464", "#C84646", "#FFB4B4", "#FF7878"),
}
# body, body_dark, accent, inner — same layout for all characters

STATE_BUBBLE_TEXT = {
    AnimationState.IDLE:     "zzZ... GPU在休息~",
    AnimationState.SLEEPING: "Zzz... 好安静...",
    AnimationState.NORMAL:   "状态良好~",
    AnimationState.WORKING:  "正在工作中!",
    AnimationState.WARNING:  "有点热了... 注意!",
    AnimationState.CRITICAL: "太热了!!! 快关程序!",
}


class ProceduralAnimator:
    def __init__(self):
        self._state: AnimationState = AnimationState.NORMAL
        self._prev_state: Optional[AnimationState] = None
        self._anim_time: float = 0.0
        self._transition_progress: float = 1.0
        self._is_transitioning: bool = False
        self._transition_duration: float = 0.4
        self._custom_text: str = ""
        self._bob_offset: float = 0.0
        self._tail_angle: float = 0.0
        self._blink_timer: float = 0.0
        self._blink_visible: bool = True
        self._ear_wiggle: float = 0.0
        self._sweat_visible: bool = False
        self._smoke_offset: float = 0.0
        self._character_type: str = "cat"
        self._mouse_x: float = 0.0
        self._mouse_y: float = 0.0
        self._hover_active: bool = False
        self._hover_wave: float = 0.0

    # ── Public API ──────────────────────────────────────
    def set_character(self, char_type: str):
        self._character_type = char_type

    def set_mouse(self, x, y, active):
        if active and not self._hover_active:
            self._hover_active = True
        self._mouse_x, self._mouse_y = x, y
        self._hover_active = active

    @property
    def current_state(self) -> AnimationState:
        return self._state

    def set_state(self, new_state, transition_ms=400, custom_text=""):
        if new_state == self._state:
            self._custom_text = custom_text or self._custom_text
            return
        self._prev_state = self._state
        self._state = new_state
        self._is_transitioning = True
        self._transition_progress = 0.0
        self._transition_duration = transition_ms / 1000.0
        self._custom_text = custom_text
        self._sweat_visible = new_state in (AnimationState.WARNING, AnimationState.CRITICAL)

    def update(self, dt: float):
        self._anim_time += dt
        if self._is_transitioning:
            self._transition_progress += dt / max(0.001, self._transition_duration)
            if self._transition_progress >= 1.0:
                self._transition_progress = 1.0
                self._is_transitioning = False
                self._prev_state = None

        # Bob
        spd = {"idle": 0.6, "sleeping": 0.3, "normal": 1.0, "working": 1.5, "warning": 2.0, "critical": 3.5}
        amp = {"idle": 4, "sleeping": 2, "normal": 5, "working": 5, "warning": 7, "critical": 10}
        self._bob_offset = math.sin(self._anim_time * spd.get(self._state.value, 1.0)) * amp.get(self._state.value, 5)

        # Tail
        tspd = {"idle": 1.0, "sleeping": 0.4, "normal": 1.5, "working": 2.0, "warning": 4.0, "critical": 6.0}
        self._tail_angle = math.sin(self._anim_time * tspd.get(self._state.value, 1.5)) * 25

        # Blink
        self._blink_timer += dt
        self._blink_visible = not (0.1 < self._blink_timer % 4.0 < 0.15)

        # Hover
        self._hover_wave += dt * (4 if self._hover_active else -3)
        self._hover_wave = max(0.0, min(1.0, self._hover_wave))

        # Sweat
        if self._sweat_visible:
            self._smoke_offset = (self._smoke_offset + dt * 30) % 40

    # ── Color helpers ────────────────────────────────────
    def _color(self, idx: int) -> QColor:
        key = self._state
        if self._is_transitioning and self._prev_state:
            a = QColor(STATE_COLORS.get(self._prev_state, STATE_COLORS[AnimationState.NORMAL])[idx])
            b = QColor(STATE_COLORS.get(key, STATE_COLORS[AnimationState.NORMAL])[idx])
            t = self._transition_progress
            return QColor(
                int(a.red() + (b.red() - a.red()) * t),
                int(a.green() + (b.green() - a.green()) * t),
                int(a.blue() + (b.blue() - a.blue()) * t),
            )
        return QColor(STATE_COLORS.get(key, STATE_COLORS[AnimationState.NORMAL])[idx])

    # ── Coordinate helper ───────────────────────────────
    def _si(self, v): return int(v)

    # ── Render dispatch ─────────────────────────────────
    def render(self, painter: QPainter, width: int, height: int):
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = width // 2, height // 2 + 5 + int(self._bob_offset)
        self._s = min(width / 200.0, height / 230.0)
        s = self._s

        draw = getattr(self, f"_draw_{self._character_type}", self._draw_cat)
        draw(painter, cx, cy, s)

        if self._sweat_visible:
            self._draw_sweat(painter, cx, cy, s)
        text = self._custom_text or STATE_BUBBLE_TEXT.get(self._state, "")
        self._draw_bubble(painter, cx, cy, s, text)

    # ── Eye tracking utility ─────────────────────────────
    def _track(self, s):
        if self._hover_active:
            dx = (self._mouse_x - 85) / 85 * 3 * s
            dy = (self._mouse_y - 100) / 100 * 3 * s
        else:
            dx = dy = 0
        return max(-3 * s, min(3 * s, dx)), max(-3 * s, min(3 * s, dy))

    def _draw_eyes(self, p, cx, cy, s, eye_c, accent, spacing=14, size_w=12, size_h=14):
        eye_y = cy - 4 * s
        tr = self._track(s)
        for side in (-1, 1):
            ex = cx + side * int(spacing * s)
            # White
            p.setBrush(QColor(255, 255, 255))
            p.setPen(QPen(eye_c, int(2 * s)))
            p.drawEllipse(QRect(int(ex - size_w * s), int(eye_y - size_h * s),
                                int(size_w * 2 * s), int(size_h * 2 * s)))
            if self._blink_visible:
                p.setBrush(eye_c)
                p.setPen(Qt.NoPen)
                px = ex + int(tr[0])
                py = eye_y + int(tr[1])
                p.drawEllipse(QRect(int(px - 4 * s), int(py - 5 * s),
                                    int(8 * s), int(10 * s)))
                p.setBrush(QColor(255, 255, 255))
                p.drawEllipse(QRect(int(ex + 3 * s), int(eye_y - 6 * s),
                                    int(5 * s), int(5 * s)))
            else:
                p.setPen(QPen(eye_c, int(2 * s)))
                p.drawLine(int(ex - size_w * s - 1), int(eye_y),
                           int(ex + size_w * s + 1), int(eye_y))

    # ══════════════════════════════════════════════════════
    #  CHARACTERS
    # ══════════════════════════════════════════════════════

    # ── 1. Cat ───────────────────────────────────────────
    def _draw_cat(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        bw, bh = int(70 * s), int(65 * s)
        grad = QLinearGradient(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
        grad.setColorAt(0, body.lighter(110)); grad.setColorAt(1, dark)
        p.setBrush(grad); p.setPen(QPen(dark, int(2 * s)))
        p.drawRoundedRect(cx - bw // 2, cy - bh // 2, bw, bh, int(30 * s), int(30 * s))
        # Ears
        for side in (-1, 1):
            ex, ey = cx + side * int(18 * s), cy - int(25 * s)
            path = QPainterPath()
            path.moveTo(ex - 11 * s, ey + 14 * s); path.lineTo(ex - 8 * s, ey - 14 * s)
            path.lineTo(ex + 8 * s, ey - 14 * s); path.lineTo(ex + 11 * s, ey + 14 * s)
            path.closeSubpath()
            p.setBrush(body.lighter(110)); p.setPen(QPen(dark, int(2 * s))); p.drawPath(path)
            ip = QPainterPath()
            ip.moveTo(ex - 7 * s, ey + 10 * s); ip.lineTo(ex - 4 * s, ey - 8 * s)
            ip.lineTo(ex + 4 * s, ey - 8 * s); ip.lineTo(ex + 7 * s, ey + 10 * s)
            ip.closeSubpath()
            p.setBrush(inner); p.setPen(Qt.NoPen); p.drawPath(ip)
        # Face
        self._draw_eyes(p, cx, cy, s, dark, accent)
        p.setBrush(QColor(255, 150, 150)); p.setPen(QPen(QColor(200, 100, 100), int(1 * s)))
        p.drawEllipse(QRect(int(cx - 4 * s), int(cy + 5 * s), int(8 * s), int(6 * s)))
        p.setPen(QPen(dark, int(1.5 * s)))
        for side in (-1, 1):
            path = QPainterPath(); path.moveTo(cx, cy + 9 * s)
            path.cubicTo(cx + side * 3 * s, cy + 12 * s, cx + side * 7 * s, cy + 8 * s, cx + side * 10 * s, cy + 13 * s)
            p.drawPath(path)
        # Whiskers
        p.setPen(QPen(QColor(255, 255, 255, 120), int(1 * s)))
        for side in (-1, 1):
            for dy in (-3, 1, 5):
                p.drawLine(int(cx + side * 6 * s), int(cy + (7 + dy) * s),
                           int(cx + side * 22 * s), int(cy + (7 + dy * 1.5) * s))
        # Tail
        p.save(); p.translate(int(cx + 30 * s), int(cy + 10 * s)); p.rotate(self._tail_angle)
        grad2 = QLinearGradient(0, -8 * s, 0, 27 * s)
        grad2.setColorAt(0, body); grad2.setColorAt(1, dark)
        p.setBrush(grad2); p.setPen(QPen(dark, int(1.5 * s)))
        p.drawRoundedRect(int(-5 * s), int(-8 * s), int(10 * s), int(35 * s), int(5 * s), int(5 * s))
        p.restore()
        # Colored scarf band (no text)
        p.setBrush(accent); p.setPen(QPen(accent.darker(120), int(1.5 * s)))
        p.drawRoundedRect(int(cx - 25 * s), int(cy + 26 * s), int(50 * s), int(10 * s), int(4 * s), int(4 * s))

    # ── 2. Robot ─────────────────────────────────────────
    def _draw_robot(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        bw, bh = int(70 * s), int(64 * s)
        grad = QLinearGradient(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
        grad.setColorAt(0, body.lighter(120)); grad.setColorAt(1, dark)
        p.setBrush(grad); p.setPen(QPen(dark, int(2.5 * s)))
        p.drawRoundedRect(cx - bw // 2, cy - bh // 2, bw, bh, int(14 * s), int(14 * s))
        # Antenna
        ant_top = cy - bh // 2 - int(16 * s)
        p.setPen(QPen(dark, int(2 * s))); p.drawLine(cx, int(cy - bh // 2), cx, ant_top)
        p.setBrush(accent); p.setPen(Qt.NoPen)
        r = int(5 * s); p.drawEllipse(QRect(cx - r, ant_top - r, r * 2, r * 2))
        # Screen
        sw, sh = int(46 * s), int(36 * s)
        sx, sy = cx - sw // 2, cy - int(10 * s)
        p.setBrush(QColor(20, 30, 40)); p.setPen(QPen(accent, int(1.5 * s)))
        p.drawRoundedRect(sx, sy, sw, sh, int(7 * s), int(7 * s))
        # Screen eyes
        tr = self._track(s)
        for side in (-1, 1):
            ex = cx + side * int(10 * s) + int(tr[0])
            ey = sy + int(10 * s) + int(tr[1])
            if self._blink_visible:
                p.setBrush(accent); p.setPen(Qt.NoPen)
                p.drawEllipse(QRect(int(ex - 4 * s), int(ey - 5 * s), int(8 * s), int(10 * s)))
            else:
                p.setPen(QPen(accent, int(2 * s)))
                p.drawLine(int(ex - 5 * s), int(ey), int(ex + 5 * s), int(ey))
        # Screen mouth
        my = sy + int(28 * s); mw = int(12 * s)
        p.setPen(QPen(accent, int(1.5 * s)))
        if self._state == AnimationState.CRITICAL:
            p.setBrush(accent); p.drawEllipse(QRect(cx - mw // 2, my - mw // 2, mw, mw))
        elif self._state in (AnimationState.WARNING, AnimationState.WORKING):
            p.drawLine(cx - mw // 2, my, cx + mw // 2, my)
        else:
            path = QPainterPath(); path.moveTo(cx - mw // 2, my)
            path.quadTo(cx, my + int(4 * s), cx + mw // 2, my); p.drawPath(path)
        # Joint rings
        for side in (-1, 1):
            jx, jy = cx + side * int(32 * s), cy + int(5 * s)
            jr = int(6 * s)
            p.setBrush(dark); p.setPen(QPen(accent, int(1.5 * s)))
            p.drawEllipse(QRect(jx - jr, jy - jr, jr * 2, jr * 2))
        # Bottom accent stripe (no text)
        p.setBrush(accent); p.setPen(QPen(accent.darker(130), int(1 * s)))
        p.drawRoundedRect(cx - int(22 * s), cy + bh // 2 - int(5 * s), int(44 * s), int(8 * s), int(3 * s), int(3 * s))

    # ── 3. Fox ───────────────────────────────────────────
    def _draw_fox(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        # Body — slightly oval
        bw, bh = int(60 * s), int(70 * s)
        grad = QLinearGradient(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
        grad.setColorAt(0, body.lighter(110)); grad.setColorAt(1, dark)
        p.setBrush(grad); p.setPen(QPen(dark, int(2 * s)))
        p.drawEllipse(QRect(cx - bw // 2, cy - bh // 2, bw, bh))
        # Pointy ears
        for side in (-1, 1):
            ex, ey = cx + side * int(14 * s), cy - bh // 2 - int(8 * s)
            path = QPainterPath()
            path.moveTo(ex - 8 * s, ey + 18 * s); path.lineTo(ex - 3 * s, ey - 10 * s)
            path.lineTo(ex + 10 * s, ey + 8 * s); path.lineTo(ex + 8 * s, ey + 18 * s)
            path.closeSubpath()
            p.setBrush(body.lighter(110)); p.setPen(QPen(dark, int(2 * s))); p.drawPath(path)
            ip = QPainterPath()
            ip.moveTo(ex - 5 * s, ey + 14 * s); ip.lineTo(ex - 1 * s, ey - 4 * s)
            ip.lineTo(ex + 6 * s, ey + 10 * s); ip.lineTo(ex + 5 * s, ey + 14 * s)
            ip.closeSubpath()
            p.setBrush(inner); p.setPen(Qt.NoPen); p.drawPath(ip)
        # Face (white lower face)
        p.setBrush(QColor(255, 255, 255, 180)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRect(int(cx - 18 * s), int(cy + 2 * s), int(36 * s), int(28 * s)))
        self._draw_eyes(p, cx, cy, s, dark, accent, spacing=12, size_w=10, size_h=12)
        # Nose tip
        p.setBrush(QColor(50, 50, 50)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRect(int(cx - 3 * s), int(cy + 10 * s), int(6 * s), int(4 * s)))
        # Bushy tail
        p.save(); p.translate(int(cx + 28 * s), int(cy - 5 * s)); p.rotate(self._tail_angle * 0.7 + 30)
        grad2 = QLinearGradient(0, 0, 0, int(40 * s))
        grad2.setColorAt(0, body); grad2.setColorAt(0.7, body.lighter(120)); grad2.setColorAt(1, QColor(255, 255, 255, 200))
        p.setBrush(grad2); p.setPen(QPen(dark, int(1.5 * s)))
        p.drawRoundedRect(int(-8 * s), int(-4 * s), int(16 * s), int(38 * s), int(8 * s), int(8 * s))
        p.restore()

    # ── 4. Bunny ─────────────────────────────────────────
    def _draw_bunny(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        # Body
        bw, bh = int(60 * s), int(62 * s)
        grad = QLinearGradient(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
        grad.setColorAt(0, body.lighter(120)); grad.setColorAt(1, dark)
        p.setBrush(grad); p.setPen(QPen(dark, int(2 * s)))
        p.drawEllipse(QRect(cx - bw // 2, cy - bh // 2, bw, bh))
        # Long floppy ears
        for side in (-1, 1):
            ex = cx + side * int(12 * s)
            ear_path = QPainterPath()
            ear_path.moveTo(ex - 6 * s, cy - int(5 * s))
            ear_path.cubicTo(ex - int(8 * s), cy - int(35 * s), ex + int(5 * s), cy - int(45 * s), ex + int(2 * s), cy - int(55 * s))
            ear_path.cubicTo(ex + int(6 * s), cy - int(35 * s), ex + int(2 * s), cy - int(10 * s), ex + 6 * s, cy - int(5 * s))
            ear_path.closeSubpath()
            p.setBrush(body.lighter(110)); p.setPen(QPen(dark, int(2 * s))); p.drawPath(ear_path)
            # Inner ear
            ie = QPainterPath()
            ie.moveTo(ex - 3 * s, cy - int(8 * s))
            ie.cubicTo(ex - int(5 * s), cy - int(25 * s), ex + int(2 * s), cy - int(35 * s), ex + int(1 * s), cy - int(40 * s))
            ie.cubicTo(ex + int(3 * s), cy - int(25 * s), ex + int(1 * s), cy - int(10 * s), ex + 3 * s, cy - int(8 * s))
            p.setBrush(inner); p.setPen(Qt.NoPen); p.drawPath(ie)
        # Face
        self._draw_eyes(p, cx, cy, s, dark, accent, spacing=12, size_w=10, size_h=12)
        p.setBrush(QColor(255, 150, 150)); p.setPen(QPen(QColor(200, 100, 100), int(1 * s)))
        p.drawEllipse(QRect(int(cx - 3 * s), int(cy + 6 * s), int(6 * s), int(4 * s)))
        p.setPen(QPen(dark, int(1 * s)))
        p.drawLine(cx, int(cy + 10 * s), cx, int(cy + 14 * s))
        p.drawLine(int(cx - 4 * s), int(cy + 12 * s), cx, int(cy + 14 * s))
        p.drawLine(int(cx + 4 * s), int(cy + 12 * s), cx, int(cy + 14 * s))
        # Puff tail
        p.setBrush(QColor(255, 255, 255, 220)); p.setPen(QPen(QColor(220, 220, 220), int(1 * s)))
        p.drawEllipse(QRect(int(cx + 22 * s), int(cy + 14 * s), int(16 * s), int(14 * s)))

    # ── 5. Demon ─────────────────────────────────────────
    def _draw_demon(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        # Body
        bw, bh = int(62 * s), int(60 * s)
        grad = QLinearGradient(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
        grad.setColorAt(0, body.lighter(110)); grad.setColorAt(1, dark)
        p.setBrush(grad); p.setPen(QPen(dark, int(2 * s)))
        p.drawEllipse(QRect(cx - bw // 2, cy - bh // 2, bw, bh))
        # Horns
        for side in (-1, 1):
            hx = cx + side * int(14 * s); hy = cy - bh // 2 + int(5 * s)
            path = QPainterPath()
            path.moveTo(hx - 5 * s, hy); path.quadTo(hx - 5 * s + side * 2, hy - int(20 * s), hx + side * 4, hy - int(24 * s))
            path.quadTo(hx + side * 2, hy - int(15 * s), hx + 5 * s, hy)
            path.closeSubpath()
            p.setBrush(dark.darker(120)); p.setPen(QPen(dark, int(2 * s))); p.drawPath(path)
        # Bat wings
        for side in (-1, 1):
            wx = cx + side * int(28 * s); wy = cy - int(15 * s)
            wpath = QPainterPath()
            wpath.moveTo(wx, wy)
            wpath.quadTo(wx + side * int(22 * s), wy - int(20 * s), wx + side * int(25 * s), wy - int(5 * s))
            wpath.quadTo(wx + side * int(15 * s), wy + int(8 * s), wx, wy + int(10 * s))
            wpath.closeSubpath()
            p.setBrush(dark); p.setPen(QPen(dark.darker(140), int(1 * s))); p.drawPath(wpath)
        # Face
        self._draw_eyes(p, cx, cy, s, dark, accent, spacing=14, size_w=11, size_h=14)
        # Grin
        p.setPen(QPen(dark, int(2 * s))); p.setBrush(QColor(40, 20, 20))
        p.drawEllipse(QRect(int(cx - 8 * s), int(cy + 8 * s), int(16 * s), int(10 * s)))
        p.setBrush(QColor(255, 255, 255)); p.setPen(Qt.NoPen)
        for side in (-1, 1):
            p.drawRect(QRect(int(cx + side * 4 * s - 2 * s), int(cy + 10 * s), int(4 * s), int(4 * s)))
        # Pointed tail
        p.save(); p.translate(int(cx + 28 * s), int(cy + 10 * s)); p.rotate(self._tail_angle * 0.5 + 20)
        p.setBrush(dark); p.setPen(QPen(dark.darker(140), int(1 * s)))
        tail = QPainterPath(); tail.moveTo(0, 0)
        tail.quadTo(-3 * s, int(12 * s), -5 * s, int(25 * s))
        tail.quadTo(0, int(18 * s), 3 * s, int(25 * s))
        tail.quadTo(3 * s, int(12 * s), 0, 0)
        p.drawPath(tail)
        p.restore()

    # ── 6. Slime ─────────────────────────────────────────
    def _draw_slime(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        # Squishy blob body — width varies with bob
        squish = 1.0 + math.sin(self._anim_time * 2) * 0.06
        bw, bh = int(72 * s * squish), int(60 * s / squish)
        grad = QLinearGradient(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
        grad.setColorAt(0, body.lighter(140)); grad.setColorAt(0.5, body); grad.setColorAt(1, dark)
        p.setBrush(grad); p.setPen(QPen(dark, int(2 * s)))
        p.drawEllipse(QRect(cx - bw // 2, cy - bh // 2, bw, bh))
        # Highlight
        p.setBrush(QColor(255, 255, 255, 60)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRect(int(cx - 15 * s), int(cy - bh // 2 + 5 * s), int(18 * s), int(14 * s)))
        # Simple dot eyes (no white bg)
        tr = self._track(s)
        for side in (-1, 1):
            ex = cx + side * int(12 * s) + int(tr[0])
            ey = cy - int(4 * s) + int(tr[1])
            if self._blink_visible:
                p.setBrush(dark); p.setPen(Qt.NoPen)
                p.drawEllipse(QRect(ex - int(5 * s), ey - int(5 * s), int(10 * s), int(10 * s)))
            else:
                p.setPen(QPen(dark, int(2 * s)))
                p.drawLine(int(ex - 5 * s), int(ey), int(ex + 5 * s), int(ey))
        # Simple mouth
        p.setPen(QPen(dark, int(1.5 * s)))
        if self._state == AnimationState.CRITICAL:
            p.setBrush(dark); p.drawEllipse(QRect(int(cx - 5 * s), int(cy + 8 * s), int(10 * s), int(8 * s)))
        else:
            p.drawArc(cx - int(6 * s), int(cy + 6 * s), int(12 * s), int(8 * s), 0, -180 * 16)

    # ── 7. Penguin ───────────────────────────────────────
    def _draw_penguin(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        # Body — oval
        bw, bh = int(58 * s), int(72 * s)
        p.setBrush(QColor(40, 45, 55)); p.setPen(QPen(QColor(30, 35, 45), int(2 * s)))
        p.drawEllipse(QRect(cx - bw // 2, cy - bh // 2, bw, bh))
        # White belly
        p.setBrush(QColor(240, 245, 250)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRect(int(cx - 18 * s), int(cy - 2 * s), int(36 * s), int(38 * s)))
        # Flippers (use body color for state indication)
        for side in (-1, 1):
            fx = cx + side * int(28 * s); fy = cy - int(5 * s)
            fp = QPainterPath()
            fp.moveTo(fx, fy); fp.quadTo(fx + side * int(14 * s), fy + int(5 * s), fx + side * int(10 * s), fy + int(25 * s))
            fp.quadTo(fx + side * int(2 * s), fy + int(20 * s), fx, fy + int(12 * s))
            fp.closeSubpath()
            p.setBrush(body); p.setPen(QPen(dark, int(1.5 * s))); p.drawPath(fp)
        # Eyes
        for side in (-1, 1):
            ex = cx + side * int(10 * s); ey = cy - int(14 * s)
            p.setBrush(QColor(255, 255, 255)); p.setPen(QPen(QColor(30, 35, 45), int(2 * s)))
            p.drawEllipse(QRect(ex - int(7 * s), ey - int(8 * s), int(14 * s), int(14 * s)))
            if self._blink_visible:
                p.setBrush(QColor(30, 35, 45)); p.setPen(Qt.NoPen)
                tr = self._track(s)
                p.drawEllipse(QRect(int(ex + tr[0] - 3 * s), int(ey + tr[1] - 3 * s), int(6 * s), int(7 * s)))
            else:
                p.setPen(QPen(QColor(30, 35, 45), int(2 * s)))
                p.drawLine(int(ex - 7 * s), int(ey), int(ex + 7 * s), int(ey))
        # Beak
        p.setBrush(QColor(255, 160, 50)); p.setPen(QPen(QColor(200, 120, 30), int(1 * s)))
        path = QPainterPath(); path.moveTo(cx, cy + 4 * s)
        path.lineTo(cx - 6 * s, cy); path.lineTo(cx - 4 * s, cy + 8 * s)
        path.lineTo(cx, cy + 6 * s); path.lineTo(cx + 4 * s, cy + 8 * s)
        path.lineTo(cx + 6 * s, cy); path.closeSubpath()
        p.drawPath(path)
        # Feet
        for side in (-1, 1):
            p.setBrush(QColor(255, 160, 50)); p.setPen(QPen(QColor(200, 120, 30), int(1 * s)))
            p.drawEllipse(QRect(int(cx + side * 10 * s - 8 * s), int(cy + bh // 2 - 6 * s), int(16 * s), int(8 * s)))

    # ── 8. Hamster ───────────────────────────────────────
    def _draw_hamster(self, p, cx, cy, s):
        body, dark, accent, inner = self._color(0), self._color(1), self._color(2), self._color(3)
        # Round chubby body
        bw, bh = int(66 * s), int(60 * s)
        grad = QLinearGradient(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
        grad.setColorAt(0, body.lighter(120)); grad.setColorAt(1, dark)
        p.setBrush(grad); p.setPen(QPen(dark, int(2 * s)))
        p.drawEllipse(QRect(cx - bw // 2, cy - bh // 2, bw, bh))
        # Tiny round ears
        for side in (-1, 1):
            ex = cx + side * int(16 * s); ey = cy - bh // 2 + int(8 * s)
            p.setBrush(body.lighter(110)); p.setPen(QPen(dark, int(1.5 * s)))
            p.drawEllipse(QRect(ex - int(10 * s), ey - int(8 * s), int(20 * s), int(16 * s)))
            p.setBrush(inner); p.setPen(Qt.NoPen)
            p.drawEllipse(QRect(ex - int(6 * s), ey - int(4 * s), int(12 * s), int(10 * s)))
        # Chubby cheeks
        for side in (-1, 1):
            p.setBrush(inner); p.setPen(Qt.NoPen)
            p.drawEllipse(QRect(int(cx + side * 14 * s - 10 * s), int(cy + 4 * s), int(20 * s), int(14 * s)))
        # Eyes (small)
        self._draw_eyes(p, cx, cy - int(2 * s), s, dark, accent, spacing=12, size_w=6, size_h=8)
        # Tiny nose & mouth
        p.setBrush(QColor(255, 150, 150)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRect(int(cx - 2 * s), int(cy + 8 * s), int(4 * s), int(3 * s)))
        p.setPen(QPen(dark, int(1 * s)))
        p.drawLine(cx, int(cy + 11 * s), cx, int(cy + 14 * s))
        p.drawLine(int(cx - 3 * s), int(cy + 13 * s), cx, int(cy + 14 * s))
        p.drawLine(int(cx + 3 * s), int(cy + 13 * s), cx, int(cy + 14 * s))
        # Tiny paws at front
        for side in (-1, 1):
            p.setBrush(body.lighter(120)); p.setPen(QPen(dark, int(1 * s)))
            p.drawEllipse(QRect(int(cx + side * 12 * s - 6 * s), int(cy + 22 * s), int(12 * s), int(8 * s)))

    # ── Sweat / smoke effects ────────────────────────────
    def _draw_sweat(self, p, cx, cy, s):
        p.setPen(QPen(QColor(150, 210, 255, 200), int(2 * s)))
        p.setBrush(QColor(180, 220, 255, 160))
        for i, off in enumerate((-1, 1)):
            dx = cx + off * int(18 * s) - self._smoke_offset * off * 0.3
            dy = cy - int(30 * s) - self._smoke_offset + i * 10
            r = int(5 * s)
            path = QPainterPath(); path.moveTo(dx, dy - r)
            path.cubicTo(dx + r, dy - r // 2, dx + r // 2, dy + r // 2, dx, dy + r)
            path.cubicTo(dx - r // 2, dy + r // 2, dx - r, dy - r // 2, dx, dy - r)
            p.drawPath(path)
        if self._state == AnimationState.CRITICAL:
            for i in range(3):
                px = cx + int((-10 + i * 10) * s) + math.sin(self._anim_time * 3 + i) * 8
                py = cy - int(40 * s) - self._smoke_offset - i * 12
                pr = int((5 + i * 2) * s)
                p.setBrush(QColor(180, 180, 180, 120 - i * 30)); p.setPen(Qt.NoPen)
                p.drawEllipse(QRect(int(px - pr), int(py - pr), pr * 2, pr * 2))

    # ── Speech bubble ────────────────────────────────────
    def _draw_bubble(self, p, cx, cy, s, text):
        if not text:
            return
        font = sans_font(max(8, int(10 * s)))
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.boundingRect(text).width() + int(24 * s)
        th = fm.height() + int(6 * s)
        bx = int(cx - tw // 2)
        body_top = cy - int(35 * s)
        by = max(int(5 * s), body_top - th - int(6 * s))
        if bx < 4: bx = 4
        if bx + tw > cx * 2 - 4: bx = cx * 2 - tw - 4

        path = QPainterPath()
        path.addRoundedRect(bx, by, tw, th, int(10 * s), int(10 * s))
        # Tail
        path.moveTo(int(cx - 6 * s), by + th)
        path.lineTo(cx, by + th + int(8 * s))
        path.lineTo(int(cx + 6 * s), by + th)
        path.closeSubpath()

        p.setBrush(QColor(255, 255, 255, 220))
        p.setPen(QPen(QColor(180, 180, 180, 150), int(1 * s)))
        p.drawPath(path)
        p.setPen(QColor(50, 50, 50))
        p.drawText(QRect(bx, by, tw, th), Qt.AlignCenter, text)
