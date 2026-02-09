from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ContentManager:
    """Simple YAML-based content loader.

    All user-facing strings and menu structures are loaded from files
    under the ``content`` directory.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent / "content"
        self._base_path = base_path
        self._texts: dict[str, Any] | None = None
        self._menus: dict[str, Any] | None = None

    def load(self) -> None:
        self._texts = self._load_yaml("texts.ru.yml")
        self._menus = self._load_yaml("menus.ru.yml")

    def reload(self) -> None:
        self.load()

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = self._base_path / filename
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected structure in content file {filename}")
        return data

    def get_text(self, key: str) -> str:
        if self._texts is None:
            self.load()
        assert self._texts is not None
        value = self._get_nested(self._texts, key)
        if not isinstance(value, str):
            raise KeyError(f"Text key '{key}' not found or not a string")
        return value

    def get_menu(self, key: str) -> list[dict[str, Any]]:
        if self._menus is None:
            self.load()
        assert self._menus is not None
        value = self._get_nested(self._menus, key)
        if not isinstance(value, list):
            raise KeyError(f"Menu key '{key}' not found or not a list")
        return value

    def _get_nested(self, data: dict[str, Any], key: str) -> Any:
        parts = key.split(".")
        current: Any = data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                raise KeyError(f"Key '{key}' not found in content")
            current = current[part]
        return current


content_manager = ContentManager()
