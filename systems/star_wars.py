import random
import re
from dataclasses import dataclass
from typing import Optional

from .banner import Banner, build_banner_lines
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


@dataclass
class StarWarsRollResult:
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
    """Parse Star Wars ND or ND+bonus notation. Returns (num_dice, bonus) or None."""
    notation = notation.strip().upper()
    match = re.fullmatch(r'(\d+)D(?:\+(\d+))?', notation)
    if not match:
        return None
    num_dice = int(match.group(1))
    bonus = int(match.group(2)) if match.group(2) else 0
    return num_dice, bonus


def roll(notation: str) -> Optional[StarWarsRollResult]:
    """Roll a Star Wars dice pool. Returns a result object or None on bad notation."""
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
                bonus_roll = random.randint(1, 6)
                rolls.append(bonus_roll)
        else:
            rolls.append(die)

    return StarWarsRollResult(
        rolls=rolls,
        bonus=bonus,
        exploded=exploded,
        complication=(special_first == 1),
    )


def print_difficulty_table() -> None:
    print("\n  Difficulty Reference:")
    print("  +-----------------+-------+")
    print("  | Difficulty      | Score |")
    print("  +-----------------+-------+")
    for label, score in DIFFICULTY_TABLE:
        print(f"  | {label:<15}  | {score:<5} |")
    print("  +-----------------+-------+")


def print_result(notation: str, result: StarWarsRollResult) -> None:
    print(f"\nRolling {notation}:")
    for i, die_val in enumerate(result.rolls):
        if i == 0:
            label = "Die 1 (special)"
            if result.exploded and len(result.rolls) > 1:
                print(f"  {label}: {die_val} -> EXPLODES! Bonus roll: {result.rolls[1]}")
                continue
            print(f"  {label}: {die_val}")
        elif i == 1 and result.exploded:
            continue  # already printed above
        else:
            print(f"  Die {i + 1}: {die_val}")

    flag_str = "  [" + " | ".join(result.flags) + "]" if result.flags else ""
    dice_sum = sum(result.rolls)
    if result.bonus:
        print(f"\n  Dice sum: {dice_sum}  +  bonus: {result.bonus}")
    print(f"  Total: {result.total}{flag_str}")


class StarWarsSystem(RpgSystem):
    name = "Star Wars D6"
    system_slug = "star_wars"

    def run(self, character: Optional[Character] = None) -> None:
        banner = Banner(build_banner_lines(self.name, character))
        banner.install()
        print_difficulty_table()
        print("\nEnter dice notation (e.g. 6D, 4D+2) or 'q' to quit.")
        prompt = "\nWhat do you do Next?> " if character else "\nRoll> "
        try:
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
                parts = raw.split(None, 1)
                if parts[0].lower() == "roll" and len(parts) > 1:
                    notation = parts[1]
                else:
                    notation = raw
                result = roll(notation)
                if result is None:
                    print(f"Invalid notation: '{notation}'. Use format like '6D' or '4D+2'.")
                else:
                    print_result(notation, result)
        finally:
            banner.uninstall()
