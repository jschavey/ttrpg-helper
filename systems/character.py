from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class Character:
    name: str
    source_file: Path
    data: dict[str, Any]

    def __str__(self) -> str:
        return self.name


def load_characters(system_slug: str) -> list[Character]:
    """Load all character YAML files from data/<system_slug>/."""
    system_dir = DATA_DIR / system_slug
    if not system_dir.is_dir():
        return []

    characters: list[Character] = []
    for path in sorted(system_dir.glob("*.yaml")):
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        name: str = data.get("meta", {}).get("name", path.stem)
        characters.append(Character(name=name, source_file=path, data=data))
    return characters
