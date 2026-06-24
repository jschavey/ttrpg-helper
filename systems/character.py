from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class Character:
    name: str
    source_file: Path
    data: dict[str, Any]
    session_hp: Optional[int] = None  # tracks current HP in-session; persisted to YAML

    def __str__(self) -> str:
        return self.name

    def save(self) -> None:
        with open(self.source_file, "w") as f:
            yaml.dump(self.data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_characters(system_slug: str) -> list[Character]:
    """Load all character YAML files from data/<system_slug>/."""
    system_dir = DATA_DIR / system_slug
    if not system_dir.is_dir():
        return []

    characters: list[Character] = []
    for path in sorted(system_dir.glob("*.yaml")):
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        name: str = (
            data.get("meta", {}).get("name")
            or data.get("character_info", {}).get("name")
            or path.stem
        )
        session_hp: Optional[int] = data.get("combat", {}).get("current_hp")
        characters.append(Character(name=name, source_file=path, data=data, session_hp=session_hp))
    return characters
