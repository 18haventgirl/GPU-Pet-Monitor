import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SkinMeta:
    id: str
    name: str = "Unknown"
    version: str = "1.0.0"
    author: str = "Unknown"
    description: str = ""
    character_type: str = "cat"
    animation_type: str = "sprite"
    default_size: Dict[str, int] = field(default_factory=lambda: {"width": 200, "height": 200})
    scale_range: List[float] = field(default_factory=lambda: [0.5, 2.0])
    bubble_style: Dict[str, Any] = field(default_factory=dict)
    expression_overlays: Dict[str, str] = field(default_factory=dict)
    animations: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkinMeta":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unknown"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "Unknown"),
            description=data.get("description", ""),
            character_type=data.get("character_type", "cat"),
            animation_type=data.get("animation_type", "sprite"),
            default_size=data.get("default_size", {"width": 200, "height": 200}),
            scale_range=data.get("scale_range", [0.5, 2.0]),
            bubble_style=data.get("bubble_style", {}),
            expression_overlays=data.get("expression_overlays", {}),
            animations=data.get("animations", {}),
        )


@dataclass
class ThemeData:
    panel_bg: str = "rgba(30, 30, 40, 0.75)"
    panel_border: str = "rgba(255, 255, 255, 0.1)"
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#B0BEC5"
    normal_color: str = "#4CAF50"
    warning_color: str = "#FF9800"
    critical_color: str = "#F44336"
    bar_normal: str = "#4CAF50"
    bar_warning: str = "#FF9800"
    bar_critical: str = "#F44336"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThemeData":
        panel = data.get("panel", {})
        text = data.get("text", {})
        progress = data.get("progress_bar", {})
        return cls(
            panel_bg=panel.get("background", cls.panel_bg),
            panel_border=panel.get("border_color", cls.panel_border),
            text_primary=text.get("primary", cls.text_primary),
            text_secondary=text.get("secondary", cls.text_secondary),
            normal_color=progress.get("normal", {}).get("color", cls.normal_color),
            warning_color=progress.get("warning", {}).get("color", cls.warning_color),
            critical_color=progress.get("critical", {}).get("color", cls.critical_color),
        )


def _get_skins_root() -> Path:
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "skins"
    return Path(__file__).parent.parent.parent / "skins"


class SkinManager:
    def __init__(self):
        self._skins: Dict[str, SkinMeta] = {}
        self._active_skin_id: str = ""
        self._active_theme: ThemeData = ThemeData()
        self._skin_dir: Path = _get_skins_root()

    @property
    def active_skin(self) -> Optional[SkinMeta]:
        return self._skins.get(self._active_skin_id)

    @property
    def active_theme(self) -> ThemeData:
        return self._active_theme

    @property
    def skin_list(self) -> List[SkinMeta]:
        return list(self._skins.values())

    def scan(self) -> List[SkinMeta]:
        self._skins.clear()
        if not self._skin_dir.exists():
            logger.warning(f"Skin directory not found: {self._skin_dir}")
            return []

        for entry in sorted(self._skin_dir.iterdir()):
            if not entry.is_dir():
                continue
            skin_json = entry / "skin.json"
            if not skin_json.exists():
                continue
            try:
                data = json.loads(skin_json.read_text(encoding="utf-8"))
                skin = SkinMeta.from_dict(data)
                self._skins[skin.id] = skin
                logger.info(f"Loaded skin: {skin.id} ({skin.name})")
            except Exception as e:
                logger.warning(f"Failed to load skin '{entry.name}': {e}")

        return self.skin_list

    def activate(self, skin_id: str) -> bool:
        if skin_id not in self._skins:
            return False

        self._active_skin_id = skin_id
        skin = self._skins[skin_id]

        # Load theme
        theme_path = self._skin_dir / skin_id / "theme.json"
        if theme_path.exists():
            try:
                data = json.loads(theme_path.read_text(encoding="utf-8"))
                self._active_theme = ThemeData.from_dict(data)
            except Exception:
                self._active_theme = ThemeData()

        logger.info(f"Activated skin: {skin.name}")
        return True

    def get_skin_path(self, skin_id: str) -> Path:
        return self._skin_dir / skin_id

    def get_animation_path(self, skin_id: str, anim_name: str) -> Optional[Path]:
        skin = self._skins.get(skin_id)
        if not skin or anim_name not in skin.animations:
            return None
        anim = skin.animations[anim_name]
        file_path = self._skin_dir / skin_id / anim.get("file", "")
        return file_path if file_path.exists() else None

    def validate_skin(self, skin_id: str) -> bool:
        skin = self._skins.get(skin_id)
        if not skin:
            return False
        required_anims = {"idle", "normal", "working", "warning", "critical"}
        return required_anims.issubset(set(skin.animations.keys()))
