import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnimationFrame:
    x: int = 0
    y: int = 0
    width: int = 128
    height: int = 128
    duration_ms: int = 100
    event: Optional[str] = None


@dataclass
class AnimationClip:
    name: str
    frames: list[AnimationFrame]
    fps: int = 8
    loop: bool = True
    sheet_width: int = 0
    sheet_height: int = 0
    frame_width: int = 128
    frame_height: int = 128
    columns: int = 4
    total_frames: int = 0

    @property
    def duration_ms(self) -> int:
        return sum(f.duration_ms for f in self.frames)

    @property
    def frame_count(self) -> int:
        return len(self.frames) if self.frames else self.total_frames


class SpriteEngine:
    def __init__(self):
        self._clips: Dict[str, AnimationClip] = {}
        self._active_clip: Optional[AnimationClip] = None
        self._next_clip: Optional[AnimationClip] = None
        self._current_frame_index: int = 0
        self._frame_elapsed: float = 0.0
        self._sprite_sheet: Any = None
        self._sprite_path: str = ""
        self._scale: float = 1.0
        self._playing: bool = False
        self._transition_progress: float = 0.0
        self._is_crossfading: bool = False
        self._prev_clip: Optional[AnimationClip] = None
        self._prev_frame_index: int = 0

    def load_spritesheet(self, path: str) -> bool:
        try:
            from PyQt5.QtGui import QPixmap
            self._sprite_sheet = QPixmap(path)
            self._sprite_path = path
            return not self._sprite_sheet.isNull()
        except ImportError:
            return False

    def add_clip(self, name: str, clip: AnimationClip) -> None:
        self._clips[name] = clip

    def add_clip_from_meta(self, meta_path: str) -> Optional[str]:
        try:
            meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            name = meta.get("name", Path(meta_path).stem)

            frames = []
            if "frames" in meta:
                for f in meta["frames"]:
                    frames.append(AnimationFrame(
                        x=f.get("x", 0), y=f.get("y", 0),
                        width=f.get("w", meta.get("frame_width", 128)),
                        height=f.get("h", meta.get("frame_height", 128)),
                        duration_ms=f.get("duration", 100),
                        event=f.get("event"),
                    ))
            else:
                cols = meta.get("columns", 4)
                total = meta.get("total_frames", 16)
                fw = meta.get("frame_width", 128)
                fh = meta.get("frame_height", 128)
                fps = meta.get("fps", 8)
                for i in range(total):
                    frames.append(AnimationFrame(
                        x=(i % cols) * fw,
                        y=(i // cols) * fh,
                        width=fw, height=fh,
                        duration_ms=1000 // fps,
                    ))

            clip = AnimationClip(
                name=name,
                frames=frames,
                fps=meta.get("fps", 8),
                loop=meta.get("loop", True),
                sheet_width=meta.get("sheet_width", 512),
                sheet_height=meta.get("sheet_height", 512),
                frame_width=meta.get("frame_width", 128),
                frame_height=meta.get("frame_height", 128),
                columns=meta.get("columns", 4),
                total_frames=len(frames),
            )
            self._clips[name] = clip
            return name
        except Exception as e:
            logger.error(f"Failed to load animation meta '{meta_path}': {e}")
            return None

    def play(self, clip_name: str, crossfade_ms: int = 0) -> bool:
        if clip_name not in self._clips:
            return False

        clip = self._clips[clip_name]

        if crossfade_ms > 0 and self._active_clip:
            self._prev_clip = self._active_clip
            self._prev_frame_index = self._current_frame_index
            self._is_crossfading = True
            self._transition_progress = 0.0
        else:
            self._is_crossfading = False

        self._active_clip = clip
        self._next_clip = None
        self._current_frame_index = 0
        self._frame_elapsed = 0.0
        self._playing = True
        return True

    def stop(self) -> None:
        self._playing = False

    def update(self, dt: float) -> Optional[str]:
        if not self._playing or not self._active_clip:
            return None

        self._frame_elapsed += dt

        if self._is_crossfading:
            duration = 300.0
            self._transition_progress = min(1.0, self._transition_progress + dt / duration)
            if self._transition_progress >= 1.0:
                self._is_crossfading = False
                self._prev_clip = None

        frames = self._active_clip.frames
        if not frames:
            return None

        frame = frames[self._current_frame_index]
        event = None

        if self._frame_elapsed >= frame.duration_ms:
            self._current_frame_index += 1
            self._frame_elapsed = 0.0

            if self._current_frame_index >= len(frames):
                if self._active_clip.loop:
                    self._current_frame_index = 0
                else:
                    self._current_frame_index = len(frames) - 1
                    event = frame.event or "clip_end"

            next_frame = frames[min(self._current_frame_index, len(frames) - 1)]
            if next_frame.event:
                event = next_frame.event

        return event

    def get_current_frame_rect(self) -> Optional[Tuple[int, int, int, int]]:
        if not self._active_clip:
            return None

        frames = self._active_clip.frames
        if not frames:
            idx = self._current_frame_index
            fw = self._active_clip.frame_width
            fh = self._active_clip.frame_height
            cols = self._active_clip.columns
            return ((idx % cols) * fw, (idx // cols) * fh, fw, fh)

        f = frames[self._current_frame_index]
        return (f.x, f.y, f.width, f.height)

    @property
    def active_clip_name(self) -> Optional[str]:
        return self._active_clip.name if self._active_clip else None

    @property
    def is_crossfading(self) -> bool:
        return self._is_crossfading

    @property
    def crossfade_progress(self) -> float:
        return self._transition_progress

    @property
    def current_frame_index(self) -> int:
        return self._current_frame_index

    @property
    def total_frames(self) -> int:
        if not self._active_clip:
            return 0
        return len(self._active_clip.frames) or self._active_clip.total_frames
