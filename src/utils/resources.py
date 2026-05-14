from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent


def get_asset_path(*parts: str) -> str:
    return str(_ROOT / "assets" / Path(*parts))


def get_skin_path(*parts: str) -> str:
    return str(_ROOT / "skins" / Path(*parts))


def get_root() -> str:
    return str(_ROOT)
