"""West End Games Star Wars D6 system (single canonical implementation)."""
from __future__ import annotations

import random
import re
import shutil
from dataclasses import dataclass
from typing import Optional

from .banner import Banner
from .base import RpgSystem
from .character import Character


DIFFICULTY_TABLE = [
    ("Very Easy",      "1-5"),
    ("Easy",           "6-10"),
    ("Moderate",       "11-15"),
    ("Difficult",      "16-20"),
    ("Very Difficult", "21-30"),
    ("Heroic",         "31+"),
]

WOUND_STATES = ["Healthy", "Stunned", "Wounded", "Incapacitated", "Mortally Wounded", "Dead"]


@dataclass
class RollResult:
    rolls: list[int]
    bonus: int
    exploded: bool
    complication: bool

    @property
    def total(self) -> int:
        return sum(self.rolls) + self.bonus

    @property
    def flags(self) -> list[str]:
        f = []
        if self.exploded:
            f.append("EXPLODE")
        if self.complication:
            f.append("COMPLICATION")
        return f


def parse_notation(notation: str) -> Optional[tuple[int, int]]:
    """Parse ND or ND+pip notation (e.g. 6D, 4D+2). Returns (num_dice, pips) or None."""
    notation = notation.strip().upper()
    match = re.fullmatch(r'(\d+)D(?:\+(\d+))?', notation)
    if not match:
        return None
    return int(match.group(1)), (int(match.group(2)) if match.group(2) else 0)


def roll(notation: str) -> Optional[RollResult]:
    parsed = parse_notation(notation)
    if parsed is None:
        return None
    num_dice, bonus = parsed

    rolls: list[int] = []
    exploded = False
    special_first = None

    for i in range(num_dice):
        die = random.randint(1, 6)
        if i == 0:
            special_first = die
            rolls.append(die)
            if die == 6:
                exploded = True
                rolls.append(random.randint(1, 6))
        else:
            rolls.append(die)

    return RollResult(
        rolls=rolls,
        bonus=bonus,
        exploded=exploded,
        complication=(special_first == 1),
    )



def print_result(notation: str, result: RollResult) -> None:
    print(f"\nRolling {notation}:")
    for i, die_val in enumerate(result.rolls):
        if i == 0:
            label = "Die 1 (special)"
            if result.exploded and len(result.rolls) > 1:
                print(f"  {label}: {die_val} -> EXPLODES! Bonus roll: {result.rolls[1]}")
                continue
            print(f"  {label}: {die_val}")
        elif i == 1 and result.exploded:
            continue
        else:
            print(f"  Die {i + 1}: {die_val}")

    flag_str = "  [" + " | ".join(result.flags) + "]" if result.flags else ""
    dice_sum = sum(result.rolls)
    if result.bonus:
        print(f"\n  Dice sum: {dice_sum}  +  pips: {result.bonus}")
    print(f"  Total: {result.total}{flag_str}")


def build_banner_lines(character: Optional[Character]) -> list[str]:
    system_name = "Star Wars D6"
    cols = shutil.get_terminal_size().columns
    inner = cols - 2

    if character is None:
        rows = [f" {system_name}  |  No character selected"]
    else:
        data = character.data
        info = data.get("character_info", {})
        attrs = data.get("attributes_and_skills", {})
        meta_game = data.get("meta_game", {})

        char_type = info.get("type", "")
        wounds = meta_game.get("wounds", "")
        fp = meta_game.get("force_points")
        cp = meta_game.get("character_points")

        identity = f" {system_name}  |  {character.name}"
        if char_type:
            identity += f"  |  {char_type}"
        rows = [identity]

        ATTRS = ["DEXTERITY", "KNOWLEDGE", "MECHANICAL", "PERCEPTION", "STRENGTH", "TECHNICAL"]
        ABBREVS = ["DEX", "KNO", "MEC", "PER", "STR", "TEC"]
        stat_parts = [
            f"{abbr} {attrs[a]['base']}"
            for abbr, a in zip(ABBREVS, ATTRS)
            if a in attrs and "base" in attrs[a]
        ]

        status_parts: list[str] = []
        if wounds:
            status_parts.append(f"Wounds: {wounds}")
        if fp is not None:
            status_parts.append(f"FP {fp}")
        if cp is not None:
            status_parts.append(f"CP {cp}")

        combined = status_parts + stat_parts
        if combined:
            rows.append(" " + "  ".join(combined))

        rows.append(" Commands: roll <ND+pips>  wound <state>")

    # Difficulty table — always shown
    rows.append(" ┄" + "┄" * (inner - 2))
    rows.append("  Difficulty        Score")
    for label, score in DIFFICULTY_TABLE:
        rows.append(f"  {label:<18} {score}")

    top = "┌" + "─" * inner + "┐"
    bot = "└" + "─" * inner + "┘"
    mid = ["│" + r.ljust(inner) + "│" for r in rows]
    return [top] + mid + [bot]


class StarWarsD6System(RpgSystem):
    name = "Star Wars D6"
    system_slug = "star-wars-d6"

    def run(self, character: Optional[object] = None) -> None:
        char = character if isinstance(character, Character) else None
        banner = Banner(build_banner_lines(char))
        banner.install()
        print("\nEnter dice notation (e.g. 6D, 4D+2) or 'q' to quit.")
        prompt = "\nWhat do you do Next?> " if char else "\nRoll> "
        try:
            self._roll_loop(prompt, char, banner)
        finally:
            banner.uninstall()

    def _roll_loop(self, prompt: str, character: Optional[Character], banner: Banner) -> None:
        while True:
            try:
                raw = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if raw.lower() in ("q", "quit", "exit"):
                break
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0].lower()

            # --- wound state tracking ---
            if cmd == "wound":
                if character is None:
                    print("No character loaded.")
                    continue
                if len(parts) < 2:
                    print("Wound states: " + ", ".join(WOUND_STATES))
                    print("Usage: wound <state>  (e.g. wound Stunned)")
                    continue
                state = " ".join(parts[1:]).title()
                if state not in WOUND_STATES:
                    print("Valid states: " + ", ".join(WOUND_STATES))
                    continue
                character.data.setdefault("meta_game", {})["wounds"] = state
                character.save()
                print(f"\n  Wound status → {state}")
                banner.redraw(build_banner_lines(character))
                continue

            # --- roll ---
            if cmd == "roll" and len(parts) > 1:
                notation = " ".join(parts[1:])
            else:
                notation = raw

            result = roll(notation)
            if result is None:
                print(f"Invalid notation: '{notation}'. Use format like '6D' or '4D+2'.")
            else:
                print_result(notation, result)
