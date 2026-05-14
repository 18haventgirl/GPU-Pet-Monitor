from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMouseEvent

from .pet_widget import PetWidget
from .info_panel import InfoPanel
from ..gpu_monitor.gpu_info import GPUInfo
from ..config.config_manager import ConfigManager


class FloatingWindow(QMainWindow):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self._dragging = False
        self._drag_pos = QPoint()
        self._use_demo = False

        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        s = self._config.settings
        self.resize(int(435 * s.window_scale), int(260 * s.window_scale))
        self.move(s.window_x, s.window_y)
        self.setWindowOpacity(s.window_opacity)

    def _setup_ui(self):
        central = QWidget()
        central.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self._pet = PetWidget(size=170)
        self._pet.setStyleSheet("background: transparent;")
        layout.addWidget(self._pet)

        self._info_panel = InfoPanel()
        self._info_panel.set_on_double_click(self._toggle_pet)
        layout.addWidget(self._info_panel)

    def update_gpu_info(self, info: GPUInfo):
        self._info_panel.update_info(info)
        state_str = info.state.value if info.state else "normal"
        self._pet.set_gpu_state(state_str)
        return state_str

    def set_display_items(self, items: list):
        self._info_panel.set_display_items(items)

    def apply_skin(self, character_type: str):
        self._pet.set_character(character_type)

    def set_use_demo(self, demo: bool):
        self._use_demo = demo
        if demo:
            self.setWindowTitle("GPU Pet Monitor (Demo)")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            pos = self.pos()
            self._config.settings.window_x = pos.x()
            self._config.settings.window_y = pos.y()
            self._config.save()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._info_panel.setVisible(not self._info_panel.isVisible())

    def _toggle_pet(self):
        self._pet.setVisible(not self._pet.isVisible())
