from functools import partial

from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QCheckBox, QComboBox, QPushButton,
    QGroupBox, QFrame, QScrollArea, QGridLayout,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette

from ..config.config_manager import ConfigManager
from ..config.settings import AppSettings
from ..skins.skin_manager import SkinManager, SkinMeta

TAB_STYLE = """
QTabWidget::pane {
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    background: rgba(20,20,30,0.85);
}
QTabBar::tab {
    padding: 8px 16px;
    margin-right: 2px;
    color: #999;
    font-size: 11px;
}
QTabBar::tab:selected {
    color: #fff;
    background: rgba(80,80,100,0.4);
    border-radius: 6px;
}
QTabBar::tab:hover {
    color: #ccc;
}
"""


class SettingsWindow(QDialog):
    def __init__(self, config: ConfigManager, skin_manager: SkinManager, gpu_list: list, parent=None):
        super().__init__(parent)
        self._config = config
        self._skin_manager = skin_manager
        self._gpu_list = gpu_list
        self._modified = False

        self.setWindowTitle("⚙ GPU Pet Monitor 设置")
        self.setFixedSize(520, 460)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.Dialog | Qt.WindowCloseButtonHint
        )
        self.setStyleSheet(TAB_STYLE)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._gpu_tab(), "🖥 GPU")
        self._tabs.addTab(self._appearance_tab(), "🎨 外观")
        self._tabs.addTab(self._data_tab(), "📊 数据")
        self._tabs.addTab(self._thresholds_tab(), "⚠ 阈值")
        self._tabs.addTab(self._notifications_tab(), "🔔 通知")
        self._tabs.addTab(self._about_tab(), "ℹ 关于")
        layout.addWidget(self._tabs)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(
            "QPushButton { background: #4CAF50; color: #fff; padding: 6px 24px; "
            "border-radius: 6px; font-weight: bold; } "
            "QPushButton:hover { background: #66BB6A; }"
        )
        save_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.1); color: #ccc; "
            "padding: 6px 24px; border-radius: 6px; } "
            "QPushButton:hover { background: rgba(255,255,255,0.2); }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # ── GPU Tab ──────────────────────────────────────────
    def _gpu_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("选择要监控的 GPU")
        lbl.setStyleSheet("color: #fff; font-size: 13px; font-weight: bold;")
        lay.addWidget(lbl)

        self._gpu_combo = QComboBox()
        self._gpu_combo.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.08); color: #fff; "
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; "
            "padding: 8px; font-size: 12px; }"
        )
        for g in self._gpu_list:
            self._gpu_combo.addItem(f"GPU {g['id']}: {g['name']}")
        lay.addWidget(self._gpu_combo)

        info = QLabel("切换 GPU 后需要重新启动监控")
        info.setStyleSheet("color: #888; font-size: 10px; margin-top: 8px;")
        lay.addWidget(info)
        lay.addStretch()
        return w

    # ── Appearance Tab ──────────────────────────────────
    def _appearance_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)

        # Skin selector — 4×2 grid
        lbl = QLabel("皮肤选择")
        lbl.setStyleSheet("color: #fff; font-size: 13px; font-weight: bold;")
        lay.addWidget(lbl)

        self._skin_buttons = []
        skin_grid = QGridLayout()
        skin_grid.setSpacing(6)
        skins = self._skin_manager.skin_list
        for i, skin in enumerate(skins):
            row, col = i // 4, i % 4
            card = QPushButton(skin.name)
            card.setCheckable(True)
            card.setFixedSize(110, 44)
            card.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.06); color: #ccc; "
                "border: 2px solid rgba(255,255,255,0.1); border-radius: 8px; "
                "font-size: 10px; } "
                "QPushButton:checked { border-color: #4FC3F7; background: rgba(79,195,247,0.15); color: #fff; } "
                "QPushButton:hover { background: rgba(255,255,255,0.1); }"
            )
            card.clicked.connect(partial(self._on_skin_selected, skin.id))
            skin_grid.addWidget(card, row, col)
            self._skin_buttons.append((skin.id, card))
        lay.addLayout(skin_grid)

        lay.addSpacing(12)

        # Window scale
        self._scale_slider = self._labeled_slider("窗口大小", 80, 200, "%")
        lay.addLayout(self._scale_slider["layout"])

        # Window opacity
        self._opacity_slider = self._labeled_slider("透明度", 50, 100, "%")
        lay.addLayout(self._opacity_slider["layout"])

        # Click through
        self._click_through_cb = QCheckBox("窗口穿透（鼠标离开后点击穿透到下层窗口）")
        self._click_through_cb.setStyleSheet(self._cb_style())
        lay.addWidget(self._click_through_cb)

        self._autostart_cb = QCheckBox("开机自启动")
        self._autostart_cb.setStyleSheet(self._cb_style())
        lay.addWidget(self._autostart_cb)

        lay.addStretch()
        return w

    # ── Data Tab ─────────────────────────────────────────
    def _data_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("采样间隔")
        lbl.setStyleSheet("color: #fff; font-size: 13px; font-weight: bold;")
        lay.addWidget(lbl)

        self._interval_combo = QComboBox()
        self._interval_combo.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.08); color: #fff; "
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; "
            "padding: 8px; }"
        )
        for ms, label in [(200, "200ms"), (500, "500ms"), (800, "800ms (默认)"),
                          (1000, "1s"), (2000, "2s"), (5000, "5s")]:
            self._interval_combo.addItem(label, ms)
        lay.addWidget(self._interval_combo)

        lay.addSpacing(16)

        lbl2 = QLabel("显示项目")
        lbl2.setStyleSheet("color: #fff; font-size: 13px; font-weight: bold;")
        lay.addWidget(lbl2)

        self._display_cbs = {}
        for key, label in [("gpu_util", "🖥 GPU 使用率"), ("vram", "💾 显存占用"),
                           ("temp", "🌡 温度"), ("power", "⚡ 功耗"),
                           ("fan", "🌀 风扇转速"), ("clock", "📡 时钟频率"),
                           ("mini_chart", "📉 迷你历史曲线")]:
            cb = QCheckBox(label)
            cb.setStyleSheet(self._cb_style())
            lay.addWidget(cb)
            self._display_cbs[key] = cb

        lay.addStretch()
        return w

    # ── Thresholds Tab ───────────────────────────────────
    def _thresholds_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollArea > QWidget > QWidget { background: transparent; } "
            "QScrollBar:vertical { width: 6px; background: rgba(255,255,255,0.05); } "
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 3px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(20, 20, 20, 20)

        self._threshold_sliders = {}
        pairs = [
            ("temp_warn", "温度警告阈值", 50, 95),
            ("temp_critical", "温度危险阈值", 55, 100),
            ("gpu_warn", "GPU 使用率警告", 30, 90),
            ("gpu_critical", "GPU 使用率危险", 40, 100),
            ("memory_warn", "显存使用率警告", 30, 90),
            ("memory_critical", "显存使用率危险", 40, 100),
            ("power_warn", "功耗警告阈值", 30, 90),
            ("power_critical", "功耗危险阈值", 40, 100),
        ]
        for key, label, lo, hi in pairs:
            s = self._labeled_slider(label, lo, hi, "%")
            lay.addLayout(s["layout"])
            self._threshold_sliders[key] = s

        lay.addStretch()
        scroll.setWidget(inner)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    # ── Notifications Tab ────────────────────────────────
    def _notifications_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)

        self._notif_cb = QCheckBox("危险状态时弹出系统通知")
        self._notif_cb.setStyleSheet(self._cb_style())
        lay.addWidget(self._notif_cb)

        self._sound_cb = QCheckBox("危险状态时播放警告音效")
        self._sound_cb.setStyleSheet(self._cb_style())
        lay.addWidget(self._sound_cb)

        info = QLabel("提示：音效功能将在后续版本完善")
        info.setStyleSheet("color: #666; font-size: 10px; margin-top: 8px;")
        lay.addWidget(info)

        lay.addStretch()
        return w

    # ── About Tab ────────────────────────────────────────
    def _about_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)

        title = QLabel("GPU Pet Monitor")
        title.setStyleSheet("color: #4FC3F7; font-size: 18px; font-weight: bold;")
        lay.addWidget(title)

        ver = QLabel("版本 1.0.0")
        ver.setStyleSheet("color: #aaa; font-size: 11px;")
        lay.addWidget(ver)

        lay.addSpacing(12)
        desc = QLabel(
            "一只可爱的桌面宠物，实时监控你的 NVIDIA GPU 状态。\n\n"
            "🐱 根据 GPU 负载自动切换表情和动画\n"
            "📊 实时显示使用率、显存、温度、功耗\n"
            "🎨 支持自定义皮肤和主题\n\n"
            "技术栈：Python 3.10+ / PyQt5 / nvidia-ml-py"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #bbb; font-size: 11px; line-height: 1.5;")
        lay.addWidget(desc)

        lay.addStretch()
        return w

    # ── Helpers ──────────────────────────────────────────
    def _labeled_slider(self, label: str, lo: int, hi: int, suffix: str) -> dict:
        row = QHBoxLayout()
        name = QLabel(label)
        name.setStyleSheet("color: #ccc; font-size: 11px; min-width: 120px;")

        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: rgba(255,255,255,0.1); "
            "border-radius: 3px; } "
            "QSlider::handle:horizontal { width: 14px; height: 14px; margin: -5px 0; "
            "background: #4FC3F7; border-radius: 7px; } "
            "QSlider::sub-page:horizontal { background: #4FC3F7; border-radius: 3px; }"
        )

        val_lbl = QLabel(f"{lo}{suffix}")
        val_lbl.setStyleSheet("color: #4FC3F7; font-size: 11px; min-width: 40px; "
                              "font-weight: bold;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        slider.valueChanged.connect(
            lambda v: val_lbl.setText(f"{v}{suffix}")
        )

        row.addWidget(name)
        row.addWidget(slider, 1)
        row.addWidget(val_lbl)
        return {"layout": row, "slider": slider, "label": val_lbl}

    def _cb_style(self) -> str:
        return (
            "QCheckBox { color: #ccc; font-size: 11px; spacing: 8px; } "
            "QCheckBox::indicator { width: 16px; height: 16px; "
            "border: 2px solid rgba(255,255,255,0.2); border-radius: 4px; "
            "background: rgba(255,255,255,0.05); } "
            "QCheckBox::indicator:checked { background: #4CAF50; border-color: #4CAF50; }"
        )

    def _on_skin_selected(self, skin_id: str):
        for sid, btn in self._skin_buttons:
            btn.setChecked(sid == skin_id)

    # ── Load / Save ──────────────────────────────────────
    def _load_values(self):
        s = self._config.settings

        # GPU
        idx = min(s.gpu_id, self._gpu_combo.count() - 1)
        self._gpu_combo.setCurrentIndex(idx)

        # Appearance
        self._scale_slider["slider"].setValue(int(s.window_scale * 100))
        self._opacity_slider["slider"].setValue(int(s.window_opacity * 100))
        self._click_through_cb.setChecked(s.click_through_enabled)
        self._autostart_cb.setChecked(s.autostart_enabled)
        for sid, btn in self._skin_buttons:
            btn.setChecked(sid == s.skin_id)

        # Data
        for i in range(self._interval_combo.count()):
            if self._interval_combo.itemData(i) == s.interval_ms:
                self._interval_combo.setCurrentIndex(i)
                break
        for key, cb in self._display_cbs.items():
            cb.setChecked(key in s.display_items)

        # Thresholds
        for key, slider_data in self._threshold_sliders.items():
            if key in s.thresholds:
                slider_data["slider"].setValue(int(s.thresholds[key]))

        # Notifications
        self._notif_cb.setChecked(s.notification_enabled)
        self._sound_cb.setChecked(s.sound_enabled)

    def _save_and_close(self):
        s = self._config.settings

        s.gpu_id = self._gpu_combo.currentIndex()
        s.window_scale = self._scale_slider["slider"].value() / 100.0
        s.window_opacity = self._opacity_slider["slider"].value() / 100.0
        s.click_through_enabled = self._click_through_cb.isChecked()
        s.autostart_enabled = self._autostart_cb.isChecked()

        # Skin
        for sid, btn in self._skin_buttons:
            if btn.isChecked():
                s.skin_id = sid
                break

        s.interval_ms = self._interval_combo.currentData() or 800

        s.display_items = [k for k, cb in self._display_cbs.items() if cb.isChecked()]

        for key, slider_data in self._threshold_sliders.items():
            s.thresholds[key] = float(slider_data["slider"].value())

        s.notification_enabled = self._notif_cb.isChecked()
        s.sound_enabled = self._sound_cb.isChecked()

        self._config.save()
        self._modified = True
        self.accept()

    @property
    def is_modified(self) -> bool:
        return self._modified
