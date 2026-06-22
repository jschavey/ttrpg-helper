"""Pinned terminal banner using ANSI scroll-region escape codes."""
from __future__ import annotations

import shutil
import sys
from typing import Optional

from .character import Character


def _write(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.flush()


def _term_size() -> tuple[int, int]:
    sz = shutil.get_terminal_size()
    return sz.columns, sz.lines


def _stat_mod(val: int) -> str:
    mod = (val - 10) // 2
    return f"+{mod}" if mod >= 0 else str(mod)


def build_banner_lines(system_name: str, character: Optional["Character"]) -> list[str]:
    w, _ = _term_size()
    inner = w - 2  # space between box edges

    if character is None:
        rows = [f" {system_name}  |  No character selected"]
    else:
        data = character.data
        meta = data.get("meta", {})
        combat = data.get("combat", {})
        stats = data.get("stats", {})

        ancestry = meta.get("ancestry", "")
        cls = meta.get("class", "")
        level = meta.get("level", "")
        hp = combat.get("hp")
        ac = combat.get("ac_normal", combat.get("ac"))

        identity = f" {system_name}  |  {character.name}"
        tag_parts = [p for p in [ancestry, cls] if p]
        if tag_parts:
            identity += "  |  " + " ".join(tag_parts)
        if level:
            identity += f"  Lv{level}"

        rows = [identity]

        stat_labels = [("STR", "str"), ("DEX", "dex"), ("CON", "con"),
                       ("INT", "int"), ("WIS", "wis"), ("CHA", "cha")]
        stat_parts = [f"{abbr} {_stat_mod(v)}" for abbr, k in stat_labels if (v := stats.get(k)) is not None]

        combat_parts = []
        if hp is not None:
            combat_parts.append(f"HP {hp}")
        if ac is not None:
            shield_ac = combat.get("ac_shield")
            ac_str = f"{ac}/{shield_ac}" if shield_ac else str(ac)
            combat_parts.append(f"AC {ac_str}")

        if combat_parts or stat_parts:
            rows.append(" " + "  ".join(combat_parts + stat_parts))

    top = "┌" + "─" * inner + "┐"
    bot = "└" + "─" * inner + "┘"
    mid = ["│" + r.ljust(inner) + "│" for r in rows]
    return [top] + mid + [bot]


class Banner:
    """Pins lines at the top of the terminal; rolls scroll in the region below."""

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.height = len(lines)

    def install(self) -> None:
        _, h = _term_size()
        _write("\033[?25l")  # hide cursor during draw
        _write("\033[2J")    # clear entire screen
        for i, line in enumerate(self.lines, 1):
            _write(f"\033[{i};1H\033[2K{line}")
        # Restrict scrolling to lines below the banner
        _write(f"\033[{self.height + 1};{h}r")
        _write(f"\033[{self.height + 1};1H")
        _write("\033[?25h")

    def uninstall(self) -> None:
        _, h = _term_size()
        _write("\033[?25l")
        _write(f"\033[1;{h}r")  # reset scroll region
        for i in range(1, self.height + 1):
            _write(f"\033[{i};1H\033[2K")
        _write("\033[1;1H")
        _write("\033[?25h")
