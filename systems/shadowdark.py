import random
import re
from dataclasses import dataclass
from typing import Optional

from .base import RpgSystem
from .character import Character


@dataclass
class ShadowdarkRollResult:
    pools: list[tuple[int, int]]  # (count, sides); negative count = subtract
    modifier: int
    rolls: list[int]              # signed individual roll values
    advantage: Optional[bool]     # True=adv, False=dis, None=normal
    # when advantage/disadvantage, both sub-results are stored
    alt_rolls: Optional[list[int]] = None

    @property
    def dice_total(self) -> int:
        return sum(self.rolls)

    @property
    def total(self) -> int:
        return self.dice_total + self.modifier

    @property
    def alt_total(self) -> Optional[int]:
        if self.alt_rolls is None:
            return None
        return sum(self.alt_rolls) + self.modifier

    @property
    def chosen_total(self) -> int:
        if self.advantage is None or self.alt_total is None:
            return self.total
        if self.advantage:
            return max(self.total, self.alt_total)
        return min(self.total, self.alt_total)


def parse_notation(notation: str) -> Optional[tuple[list[tuple[int, int]], int]]:
    """Parse Shadowdark notation. Returns ([(count, sides), ...], modifier) or None."""
    notation = notation.strip().upper()
    match = re.fullmatch(r'((?:\d*D\d+)(?:[+\-]\d*D\d+)*)(([+\-]\d+))?', notation)
    if not match:
        return None

    pools_str = match.group(1)
    modifier_str = match.group(3)

    pool_parts = re.findall(r'([+\-]?)(\d*)D(\d+)', pools_str)
    pools: list[tuple[int, int]] = []
    for sign, count_str, sides_str in pool_parts:
        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        if sign == '-':
            count = -count
        pools.append((count, sides))

    modifier = int(modifier_str) if modifier_str else 0
    return pools, modifier


def _roll_pool(pools: list[tuple[int, int]]) -> list[int]:
    results: list[int] = []
    for count, sides in pools:
        sign = -1 if count < 0 else 1
        for _ in range(abs(count)):
            results.append(sign * random.randint(1, sides))
    return results


def roll(notation: str, advantage: Optional[bool] = None) -> Optional[ShadowdarkRollResult]:
    """Roll Shadowdark dice. Returns a result object or None on bad notation."""
    parsed = parse_notation(notation)
    if parsed is None:
        return None
    pools, modifier = parsed

    rolls = _roll_pool(pools)
    alt_rolls = _roll_pool(pools) if advantage is not None else None

    return ShadowdarkRollResult(
        pools=pools,
        modifier=modifier,
        rolls=rolls,
        advantage=advantage,
        alt_rolls=alt_rolls,
    )


def print_result(notation: str, result: ShadowdarkRollResult) -> None:
    adv_label = (
        " (advantage)" if result.advantage is True
        else " (disadvantage)" if result.advantage is False
        else ""
    )
    print(f"\nRolling {notation}{adv_label}:")

    def _print_rolls(rolls: list[int], pools: list[tuple[int, int]], indent: str = "  ") -> None:
        idx = 0
        for count, sides in pools:
            sign = -1 if count < 0 else 1
            for _ in range(abs(count)):
                raw = abs(rolls[idx])
                label = f"d{sides}" if sign == 1 else f"-d{sides}"
                print(f"{indent}{label}: {raw}")
                idx += 1

    if result.advantage is None:
        _print_rolls(result.rolls, result.pools)
        if result.modifier:
            print(f"\n  Dice: {result.dice_total}  {result.modifier:+d}")
        print(f"  Total: {result.total}")
    else:
        print(f"  [Roll 1]")
        _print_rolls(result.rolls, result.pools, indent="    ")
        if result.modifier:
            print(f"    Dice: {result.dice_total}  {result.modifier:+d}")
        print(f"    Subtotal: {result.total}")

        alt_rolls = result.alt_rolls or []
        print(f"  [Roll 2]")
        _print_rolls(alt_rolls, result.pools, indent="    ")
        alt_dice = sum(alt_rolls)
        if result.modifier:
            print(f"    Dice: {alt_dice}  {result.modifier:+d}")
        print(f"    Subtotal: {result.alt_total}")

        rule = "higher" if result.advantage else "lower"
        print(f"\n  Taking {rule}: {result.chosen_total}")


class ShadowdarkSystem(RpgSystem):
    name = "Shadowdark"
    system_slug = "shadowdark"

    def run(self, character: Optional[Character] = None) -> None:
        if character:
            print(f"\n--- Playing as: {character.name} ---")
        print("\nEnter dice notation (e.g. D20, 2D6+1, D20-3) or 'q' to quit.")
        print("Append 'a' for advantage or 'd' for disadvantage (e.g. 2D6+1 a, D20 d).")
        while True:
            try:
                raw = input("\nRoll> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if raw.lower() in ("q", "quit", "exit"):
                break
            if not raw:
                continue

            parts = raw.split()
            suffix = parts[-1].lower() if len(parts) > 1 else ""
            if suffix == "a":
                notation, advantage = " ".join(parts[:-1]), True
            elif suffix == "d":
                notation, advantage = " ".join(parts[:-1]), False
            else:
                notation, advantage = raw, None

            result = roll(notation, advantage)
            if result is None:
                print(f"Invalid notation: '{notation}'. Use format like '2D6', 'D20+3', '2D6+1D4-2'.")
            else:
                print_result(notation, result)
