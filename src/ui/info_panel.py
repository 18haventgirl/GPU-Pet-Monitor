from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath, QLinearGradient, QRadialGradient,
)

from ..gpu_monitor.gpu_info import GPUInfo
from .mini_chart import MiniChart

METRIC_ICONS = {
    "gpu_util": "🖥",
    "vram": "💾",
    "temp": "🌡",
    "power": "⚡",
    "fan": "🌀",
    "clock": "📡",
}


class GlowBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._bar_h = 7
        self._color_bands = {
            "normal": QColor("#4CAF50"),
            "warning": QColor("#FF9800"),
            "critical": QColor("#F44336"),
        }
        self.setFixedHeight(10)
        self.setMinimumWidth(60)

    def set_value(self, value: float):
        self._value = max(0.0, min(100.0, value))
        self.update()

    def _band(self):
        if self._value < 60:
            return "normal"
        elif self._value < 85:
            return "warning"
        return "critical"

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self._bar_h
        y = (self.height() - h) // 2
        band = self._band()
        color = self._color_bands[band]

        # Track
        track_path = QPainterPath()
        track_path.addRoundedRect(0, y, w, h, h / 2, h / 2)
        p.setBrush(QColor(255, 255, 255, 12))
        p.setPen(Qt.NoPen)
        p.drawPath(track_path)

        if self._value <= 0:
            return

        fill_w = max(h, int(w * self._value / 100.0))

        # Glow underfill
        glow_path = QPainterPath()
        glow_path.addRoundedRect(0, y, fill_w, h, h / 2, h / 2)
        p.setBrush(QColor(color.red(), color.green(), color.blue(), 50))
        p.drawPath(glow_path)

        # Main fill with gradient
        fill_path = QPainterPath()
        fill_path.addRoundedRect(0, y, fill_w, h, h / 2, h / 2)
        grad = QLinearGradient(0, 0, fill_w, 0)
        grad.setColorAt(0.0, color.lighter(140))
        grad.setColorAt(0.5, color)
        grad.setColorAt(1.0, color.darker(110))
        p.setBrush(grad)
        p.drawPath(fill_path)

        # Gloss highlight on top
        if fill_w > 4:
            gloss_path = QPainterPath()
            gloss_path.addRoundedRect(2, y + 1, fill_w - 4, h // 2 - 1, 3, 3)
            p.setBrush(QColor(255, 255, 255, 35))
            p.drawPath(gloss_path)


class InfoPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(250)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._gpu_info: GPUInfo | None = None
        self._collapsed = False
        self._collapse_target_h = 0
        self._on_double_click = None
        self._setup_ui()

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)
        self._layout.setSpacing(4)

        # Header
        header = QLabel("GPU 状态")
        header.setStyleSheet(
            "color: #FFFFFF; font-size: 11px; font-weight: bold; "
            "border-bottom: 1px solid rgba(255,255,255,0.1); "
            "padding-bottom: 4px;"
        )
        self._layout.addWidget(header)

        self._rows = {}
        self._row_widgets = {}  # key -> (layout, icon_widget)
        items = [
            ("gpu_util", "GPU", "%"),
            ("vram", "VRAM", "GB"),
            ("temp", "TEMP", "°C"),
            ("power", "PWR", "W"),
            ("fan", "FAN", "%"),
            ("clock", "CLK", "MHz"),
        ]
        for key, label, unit in items:
            row = QHBoxLayout()
            row.setSpacing(6)

            icon_label = QLabel(METRIC_ICONS.get(key, "") + " " + label)
            icon_label.setStyleSheet(
                "color: #8899AA; font-size: 9px; font-weight: bold;"
            )
            icon_label.setFixedWidth(50)

            bar = GlowBar()
            bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            val = QLabel("--")
            val.setStyleSheet(
                "color: #E0E0E0; font-size: 9px; font-family: Consolas, DejaVu Sans Mono, monospace;"
            )
            val.setFixedWidth(62)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row.addWidget(icon_label)
            row.addWidget(bar, 1)
            row.addWidget(val)
            self._rows[key] = (val, bar, unit)
            self._row_widgets[key] = (row, icon_label, bar, val)
            self._layout.addLayout(row)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.06); margin: 4px 0;")
        self._layout.addWidget(sep)

        # Mini chart
        self._chart = MiniChart(
            width=222, height=80, max_points=60,
            metrics=["gpu", "memory", "temp"],
        )
        self._layout.addWidget(self._chart)
        self.setLayout(self._layout)

    def update_info(self, info: GPUInfo):
        self._gpu_info = info
        rows = self._rows

        self._set_row(rows, "gpu_util", f"{info.gpu_utilization:.1f}%", info.gpu_utilization)
        self._set_row(rows, "vram", f"{info.memory_used_gb:.1f}/{info.memory_total_gb:.1f}",
                      info.memory_utilization)
        self._set_row(rows, "temp", f"{info.temperature:.0f}°C",
                      min(100, info.temperature))
        if info.power_limit > 0:
            self._set_row(rows, "power", f"{info.power_draw:.0f}/{info.power_limit:.0f}",
                          info.power_utilization)
        else:
            self._set_row(rows, "power", f"{info.power_draw:.0f}W", 0)
        self._set_row(rows, "fan", f"{info.fan_speed:.0f}%", info.fan_speed)
        self._set_row(rows, "clock", f"{info.clock_sm}MHz",
                      info.clock_utilization)

        # Temp color
        if "temp" in rows:
            val, bar, _ = rows["temp"]
            t = info.temperature
            if t > 85:
                val.setStyleSheet("color: #F44336; font-size: 9px; font-family: Consolas, DejaVu Sans Mono, monospace;")
            elif t > 70:
                val.setStyleSheet("color: #FF9800; font-size: 9px; font-family: Consolas, DejaVu Sans Mono, monospace;")
            else:
                val.setStyleSheet("color: #E0E0E0; font-size: 9px; font-family: Consolas, DejaVu Sans Mono, monospace;")

        self._chart.push(info)
        self.update()

    def _set_row(self, rows, key, text, value):
        if key in rows:
            val, bar, _ = rows[key]
            val.setText(text)
            bar.set_value(value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Multi-layer glass morphism background
        # Layer 1: main fill
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 14, 14)

        # Base dark fill
        p.setBrush(QColor(22, 22, 34, 210))
        p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        p.drawPath(path)

        # Layer 2: subtle top-left light reflection
        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(0, 0, w, h // 2, 14, 14)
        p.setClipPath(highlight_path)
        grad = QLinearGradient(0, 0, 0, h // 2)
        grad.setColorAt(0.0, QColor(255, 255, 255, 12))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 14, 14)
        p.setClipping(False)

        # Layer 3: subtle border glow (top edge)
        p.setPen(QPen(QColor(255, 255, 255, 25), 1))
        p.drawLine(14, 1, w - 14, 1)

    def set_display_items(self, items: list):
        for key, (layout, icon_label, bar, val) in self._row_widgets.items():
            show = key in items
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w:
                    w.setVisible(show)
        if self._chart:
            self._chart.setVisible("mini_chart" in items)

    def set_on_double_click(self, callback):
        self._on_double_click = callback

    def mouseDoubleClickEvent(self, event):
        if self._on_double_click:
            self._on_double_click()

    def set_collapsed(self, collapsed: bool):
        self._collapsed = collapsed
        for i in range(1, self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(not collapsed)
