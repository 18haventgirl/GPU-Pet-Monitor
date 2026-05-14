from functools import partial

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import QSize, Qt
from ..utils.fonts import emoji_font


def _create_tray_pixmap(state: str = "normal", size: int = 32) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    colors = {
        "idle": QColor("#90CAF9"),
        "normal": QColor("#4CAF50"),
        "working": QColor("#FFC107"),
        "warning": QColor("#FF9800"),
        "critical": QColor("#F44336"),
        "error": QColor("#9E9E9E"),
        "no_gpu": QColor("#78909C"),
    }
    emojis = {
        "idle": "😺", "normal": "😸", "working": "🤓",
        "warning": "😰", "critical": "😱", "error": "😵", "no_gpu": "🥺",
    }

    color = colors.get(state, colors["normal"])
    emoji = emojis.get(state, emojis["normal"])

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(color)
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)

    font = emoji_font(size - 16)
    painter.setFont(font)
    painter.drawText(0, 0, size, size, Qt.AlignCenter, emoji)
    painter.end()

    return pixmap


class TrayIcon(QSystemTrayIcon):
    def __init__(self, app_instance):
        super().__init__()
        self._app = app_instance
        self._state = "normal"

        icon = QIcon(_create_tray_pixmap("normal"))
        self.setIcon(icon)
        self.setToolTip("GPU Pet Monitor")

        self._menu = QMenu()
        self._skin_menu = QMenu("皮肤")
        self._setup_menu()
        self.setContextMenu(self._menu)

        self.activated.connect(self._on_activated)

    def _setup_menu(self):
        m = self._menu  # shorthand

        self._show_action = QAction("显示/隐藏悬浮窗", m)
        self._show_action.triggered.connect(self._app.toggle_visibility)

        self._settings_action = QAction("设置", m)
        self._settings_action.triggered.connect(self._app.open_settings)

        self._rebuild_skin_menu()

        config = self._app.config_manager
        self._autostart_action = QAction("开机自启", m)
        self._autostart_action.setCheckable(True)
        self._autostart_action.setChecked(config.settings.autostart_enabled)
        self._autostart_action.triggered.connect(self._toggle_autostart)

        self._restart_action = QAction("重启程序", m)
        self._restart_action.triggered.connect(self._app.restart)

        self._quit_action = QAction("退出", m)
        self._quit_action.triggered.connect(self._app.quit)

        m.addAction(self._show_action)
        m.addAction(self._settings_action)
        m.addSeparator()
        m.addMenu(self._skin_menu)
        m.addSeparator()
        m.addAction(self._autostart_action)
        m.addSeparator()
        m.addAction(self._restart_action)
        m.addAction(self._quit_action)

    def _rebuild_skin_menu(self):
        self._skin_menu.clear()
        current_id = self._app.config_manager.settings.skin_id
        for skin in self._app.skin_manager.skin_list:
            action = QAction(skin.name, self._skin_menu)
            action.setCheckable(True)
            action.setChecked(skin.id == current_id)
            action.triggered.connect(partial(self._on_skin_selected, skin.id))
            self._skin_menu.addAction(action)

    def _on_skin_selected(self, skin_id: str):
        self._app.switch_skin(skin_id)
        self._rebuild_skin_menu()

    def _toggle_autostart(self, enabled: bool):
        self._app.config_manager.settings.autostart_enabled = enabled
        self._app.config_manager.save()
        from ..platform.factory import get_platform_utils
        get_platform_utils().set_autostart(enabled)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._app.toggle_visibility()

    def set_state_icon(self, state: str):
        if self._state != state:
            self._state = state
            self.setIcon(QIcon(_create_tray_pixmap(state)))
