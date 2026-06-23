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
            self._roll_loop(prompt, character, banner)
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

            # --- hp ---
            if cmd == "hp":
                if character is None:
                    print("No character loaded — hp requires a character sheet.")
                    continue
                if len(parts) < 2 or not re.fullmatch(r'[+\-]\d+|\d+', parts[1]):
                    print("Usage: hp +N or hp -N  (e.g. hp -5, hp +2)")
                    continue
                delta = int(parts[1])
                max_hp = character.data.get("combat", {}).get("hp", 0)
                old_hp = character.session_hp if character.session_hp is not None else max_hp
                new_hp = old_hp + delta
                character.session_hp = new_hp
                character.data.setdefault("combat", {})["current_hp"] = new_hp
                character.save()
                sign = f"+{delta}" if delta >= 0 else str(delta)
                print(f"\n  HP {old_hp} → {new_hp}  ({sign})")
                if new_hp <= 0:
                    print("  *** CHARACTER IS DOWN (0 HP or below)! ***")
                banner.redraw(build_banner_lines(self.name, character))
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
