"""Cross-platform font fallback."""

import sys
from PyQt5.QtGui import QFont

if sys.platform == "win32":
    _FONT_SANS = "Microsoft YaHei"
    _FONT_MONO = "Consolas"
    _FONT_EMOJI = "Segoe UI Emoji"
else:
    _FONT_SANS = "Noto Sans CJK SC, WenQuanYi Micro Hei, Sans"
    _FONT_MONO = "DejaVu Sans Mono, Monospace"
    _FONT_EMOJI = "Noto Color Emoji, Emoji One, Sans"


def sans_font(size: int = 10, bold: bool = False) -> QFont:
    f = QFont(_FONT_SANS, size)
    if bold:
        f.setBold(True)
    return f


def mono_font(size: int = 10, bold: bool = False) -> QFont:
    f = QFont(_FONT_MONO, size)
    if bold:
        f.setBold(True)
    return f


def emoji_font(size: int = 16) -> QFont:
    return QFont(_FONT_EMOJI, size)
