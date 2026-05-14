from collections import deque
from typing import List, Optional

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient

from ..gpu_monitor.gpu_info import GPUInfo
from ..utils.fonts import mono_font, sans_font


CHART_COLORS = {
    "gpu": QColor("#4FC3F7"),
    "memory": QColor("#FFB74D"),
    "temp": QColor("#EF5350"),
    "power": QColor("#AED581"),
}

CHART_LABELS = {
    "gpu": "GPU",
    "memory": "VRAM",
    "temp": "TEMP",
    "power": "PWR",
}


class MiniChart(QWidget):
    def __init__(
        self, parent=None, width: int = 222, height: int = 80,
        max_points: int = 60,
        metrics: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._max_points = max_points
        self._metrics = metrics or ["gpu", "memory", "temp"]
        self._data: dict[str, deque[float]] = {
            m: deque(maxlen=max_points) for m in self._metrics
        }
        # Legend row height, then chart fills the rest
        self._legend_h = 16

    def set_metrics(self, metrics: List[str]) -> None:
        self._metrics = metrics
        self._data = {m: deque(maxlen=self._max_points) for m in metrics}
        self.update()

    def push(self, info: GPUInfo) -> None:
        m = self._data
        if "gpu" in m:
            m["gpu"].append(info.gpu_utilization)
        if "memory" in m:
            m["memory"].append(info.memory_utilization)
        if "temp" in m:
            m["temp"].append(min(100, info.temperature))
        if "power" in m:
            m["power"].append(info.power_utilization)
        self.update()

    def clear(self) -> None:
        for d in self._data.values():
            d.clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background card
        painter.setBrush(QColor(25, 25, 35, 200))
        painter.setPen(QPen(QColor(60, 60, 80), 1))
        painter.drawRoundedRect(0, 0, w, h, 8, 8)

        # ── Legend row at top ──────────────────────────
        legend_y = 0
        legend_h = self._legend_h

        font = mono_font(8)
        painter.setFont(font)

        # Calculate legend item width to distribute evenly
        n = len(self._metrics)
        item_w = w // max(1, n)

        for i, metric in enumerate(self._metrics):
            values = list(self._data.get(metric, []))
            latest = values[-1] if values else 0
            color = CHART_COLORS.get(metric, QColor("#FFF"))
            label = CHART_LABELS.get(metric, metric)

            lx = i * item_w + 6
            ly = 2

            # Colored dot
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(lx, ly + 4, 6, 6)

            # Label text with proper unit
            if metric in ("gpu", "memory"):
                text = f"{label} {latest:.0f}%"
            elif metric == "temp":
                text = f"{label} {latest:.0f}°"
            elif metric == "power":
                text = f"{label} {latest:.0f}%"
            else:
                text = f"{label} {latest:.0f}"
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(lx + 10, ly, item_w - 16, legend_h,
                             Qt.AlignVCenter | Qt.AlignLeft, text)

        # ── Chart area ──────────────────────────────────
        plot_x = 4
        plot_y = legend_h + 2
        plot_w = w - 8
        plot_h = h - legend_h - 6
        if plot_h < 10:
            return

        # Subtle grid
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1, Qt.DotLine))
        for frac in [0.33, 0.66]:
            gy = int(plot_y + plot_h * (1 - frac))
            painter.drawLine(plot_x, gy, plot_x + plot_w, gy)

        if not any(len(d) > 0 for d in self._data.values()):
            painter.setPen(QColor(150, 150, 150))
            font_s = sans_font(8)
            painter.setFont(font_s)
            painter.drawText(0, plot_y, w, plot_h, Qt.AlignCenter, "等待数据...")
            return

        for metric in self._metrics:
            values = list(self._data.get(metric, []))
            if len(values) < 2:
                continue
            color = CHART_COLORS.get(metric, QColor("#FFFFFF"))
            self._draw_line(painter, values, plot_x, plot_y, plot_w, plot_h, color)

    def _draw_line(self, painter, values: list, px: int, py: int, pw: int, ph: int, color: QColor):
        if len(values) < 2:
            return

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val or 1.0
        margin = range_val * 0.08
        min_val -= margin
        max_val += margin
        range_val = max_val - min_val or 1.0

        # Scale x to fit actual data points (not max_points)
        n = len(values)
        step_x = pw / max(1, n - 1)

        path = QPainterPath()
        first = True
        for i, v in enumerate(values):
            nx = px + i * step_x
            ny = py + ph * (1 - (v - min_val) / range_val)

            if first:
                path.moveTo(nx, ny)
                first = False
            else:
                prev_x = px + (i - 1) * step_x
                cx1 = prev_x + step_x * 0.5
                cx2 = nx - step_x * 0.5
                path.cubicTo(cx1, path.currentPosition().y(), cx2, ny, nx, ny)

        # Glow
        glow_pen = QPen(color.lighter(150))
        glow_pen.setWidth(3)
        glow_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Main line
        line_pen = QPen(color)
        line_pen.setWidth(1)
        line_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(line_pen)
        painter.drawPath(path)

        # Fill
        fill_path = QPainterPath(path)
        last_x = px + (n - 1) * step_x
        fill_path.lineTo(last_x, py + ph)
        fill_path.lineTo(px, py + ph)
        fill_path.closeSubpath()

        gradient = QLinearGradient(0, py, 0, py + ph)
        gradient.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 50))
        gradient.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 3))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPath(fill_path)
