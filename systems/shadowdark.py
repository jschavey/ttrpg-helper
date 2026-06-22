import random
import re
from dataclasses import dataclass
from typing import Optional

from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import Completer, Completion

from .banner import Banner, build_banner_lines
from .base import RpgSystem
from .character import Character


# Maps input aliases to (stat_key, display_name).
# Stat keys match character YAML stats section.
CHECKS: dict[str, tuple[str, str]] = {
    # direct stat names
    "str": ("str", "Strength"),       "strength": ("str", "Strength"),
    "dex": ("dex", "Dexterity"),      "dexterity": ("dex", "Dexterity"),
    "con": ("con", "Constitution"),   "constitution": ("con", "Constitution"),
    "int": ("int", "Intelligence"),   "intelligence": ("int", "Intelligence"),
    "wis": ("wis", "Wisdom"),         "wisdom": ("wis", "Wisdom"),
    "cha": ("cha", "Charisma"),       "charisma": ("cha", "Charisma"),
    # common named checks → underlying stat
    "perception": ("wis", "Perception"),   "perc": ("wis", "Perception"),
    "insight": ("wis", "Insight"),         "ins": ("wis", "Insight"),
    "medicine": ("wis", "Medicine"),       "med": ("wis", "Medicine"),
    "survival": ("wis", "Survival"),       "surv": ("wis", "Survival"),
    "animal handling": ("wis", "Animal Handling"), "ani": ("wis", "Animal Handling"),
    "stealth": ("dex", "Stealth"),         "stl": ("dex", "Stealth"),
    "acrobatics": ("dex", "Acrobatics"),   "acr": ("dex", "Acrobatics"),
    "athletics": ("str", "Athletics"),     "ath": ("str", "Athletics"),
    "arcana": ("int", "Arcana"),           "arc": ("int", "Arcana"),
    "history": ("int", "History"),         "hist": ("int", "History"),
    "investigation": ("int", "Investigation"), "inv": ("int", "Investigation"),
    "nature": ("int", "Nature"),           "nat": ("int", "Nature"),
    "religion": ("int", "Religion"),       "rel": ("int", "Religion"),
    "persuasion": ("cha", "Persuasion"),   "pers": ("cha", "Persuasion"),
    "deception": ("cha", "Deception"),     "dec": ("cha", "Deception"),
    "intimidation": ("cha", "Intimidation"), "intim": ("cha", "Intimidation"),
}

# Spellcasting stat per class (lowercase class name → stat key).
_SPELLCASTING_STAT: dict[str, str] = {
    "priest": "wis",
    "wizard": "int",
}

# Talent text that grants +1 to spellcasting, keyed by class.
_SPELLCASTING_TALENT: dict[str, str] = {
    "priest": "+1 to priest spellcasting checks",
}


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check_name: str
    stat_key: str
    stat_value: int
    die_roll: int
    modifiers: list[tuple[str, int]]
    advantage: Optional[bool] = None
    alt_die_roll: Optional[int] = None

    @property
    def total(self) -> int:
        return self.die_roll + sum(v for _, v in self.modifiers)

    @property
    def alt_total(self) -> Optional[int]:
        if self.alt_die_roll is None:
            return None
        return self.alt_die_roll + sum(v for _, v in self.modifiers)

    @property
    def chosen_total(self) -> int:
        if self.advantage is None or self.alt_total is None:
            return self.total
        if self.advantage:
            return max(self.total, self.alt_total)
        return min(self.total, self.alt_total)


def check(check_name: str, character: "Character", advantage: Optional[bool] = None) -> Optional[CheckResult]:
    """Roll a D20 ability check. Returns None if check_name is unrecognised."""
    entry = CHECKS.get(check_name.lower())
    if entry is None:
        return None
    stat_key, display_name = entry
    stat_value = character.data.get("stats", {}).get(stat_key)
    if stat_value is None:
        return None
    stat_mod = (stat_value - 10) // 2
    modifiers: list[tuple[str, int]] = [
        (f"{stat_key.upper()} {stat_value:+d}", stat_mod),
    ]
    return CheckResult(
        check_name=display_name,
        stat_key=stat_key,
        stat_value=stat_value,
        die_roll=random.randint(1, 20),
        modifiers=modifiers,
        advantage=advantage,
        alt_die_roll=random.randint(1, 20) if advantage is not None else None,
    )


def _print_d20_roll_block(label: str, die_roll: int, modifiers: list[tuple[str, int]], col: int) -> None:
    print(f"  {label}")
    print(f"    {'D20 roll':<{col}}  {die_roll}")
    for src, value in modifiers:
        sign = f"+{value}" if value >= 0 else str(value)
        print(f"    {src:<{col}}  {sign}")
    subtotal = die_roll + sum(v for _, v in modifiers)
    print(f"    {'─' * col}  ─────")
    print(f"    {'Subtotal':<{col}}  {subtotal}")


def print_check_result(result: CheckResult) -> None:
    adv_label = " (advantage)" if result.advantage is True else " (disadvantage)" if result.advantage is False else ""
    print(f"\n{result.check_name} Check ({result.stat_key.upper()}){adv_label}")
    col = 18
    if result.advantage is None:
        print(f"  {'Source':<{col}}  Value")
        print(f"  {'-' * col}  -----")
        print(f"  {'D20 roll':<{col}}  {result.die_roll}")
        for label, value in result.modifiers:
            sign = f"+{value}" if value >= 0 else str(value)
            print(f"  {label:<{col}}  {sign}")
        print(f"  {'─' * col}  ─────")
        print(f"  {'Total':<{col}}  {result.total}")
    else:
        _print_d20_roll_block("[Roll 1]", result.die_roll, result.modifiers, col)
        _print_d20_roll_block("[Roll 2]", result.alt_die_roll or 0, result.modifiers, col)
        rule = "higher" if result.advantage else "lower"
        print(f"\n  Taking {rule}: {result.chosen_total}")


# ---------------------------------------------------------------------------
# Cast
# ---------------------------------------------------------------------------

@dataclass
class CastResult:
    spell_name: str
    die_roll: int
    modifiers: list[tuple[str, int]]
    advantage: Optional[bool]
    alt_die_roll: Optional[int]

    @property
    def total(self) -> int:
        return self.die_roll + sum(v for _, v in self.modifiers)

    @property
    def alt_total(self) -> Optional[int]:
        if self.alt_die_roll is None:
            return None
        return self.alt_die_roll + sum(v for _, v in self.modifiers)

    @property
    def chosen_total(self) -> int:
        if self.advantage is None or self.alt_total is None:
            return self.total
        if self.advantage:
            return max(self.total, self.alt_total)
        return min(self.total, self.alt_total)


def get_character_spells(character: "Character") -> list[str]:
    """Return all spell names from the character sheet, across all tiers."""
    spells_data = character.data.get("spells", {})
    spells: list[str] = []
    for tier_spells in spells_data.values():
        if isinstance(tier_spells, list):
            spells.extend(str(s) for s in tier_spells)
    return spells


def cast(
    spell_name: str,
    character: "Character",
    situational: int = 0,
    advantage: Optional[bool] = None,
) -> CastResult:
    """Roll a spellcasting check. Applies class stat mod, talent bonuses, and situational modifier."""
    cls = character.data.get("meta", {}).get("class", "").lower()
    modifiers: list[tuple[str, int]] = []

    stat_key = _SPELLCASTING_STAT.get(cls)
    if stat_key:
        stat_value = character.data.get("stats", {}).get(stat_key, 10)
        stat_mod = (stat_value - 10) // 2
        modifiers.append((f"{stat_key.upper()} {stat_value:+d}", stat_mod))

        talent_text = _SPELLCASTING_TALENT.get(cls)
        if talent_text:
            talents: list[str] = character.data.get("talents", [])
            bonus = sum(1 for t in talents if talent_text in t.lower())
            if bonus:
                modifiers.append(("Talent bonus", bonus))

    if situational:
        label = f"Situational {situational:+d}"
        modifiers.append((label, situational))

    return CastResult(
        spell_name=spell_name,
        die_roll=random.randint(1, 20),
        modifiers=modifiers,
        advantage=advantage,
        alt_die_roll=random.randint(1, 20) if advantage is not None else None,
    )


def print_cast_result(result: CastResult) -> None:
    adv_label = " (advantage)" if result.advantage is True else " (disadvantage)" if result.advantage is False else ""
    print(f"\nCast: {result.spell_name}{adv_label}")
    col = 20
    if result.advantage is None:
        print(f"  {'Source':<{col}}  Value")
        print(f"  {'-' * col}  -----")
        print(f"  {'D20 roll':<{col}}  {result.die_roll}")
        for label, value in result.modifiers:
            sign = f"+{value}" if value >= 0 else str(value)
            print(f"  {label:<{col}}  {sign}")
        print(f"  {'─' * col}  ─────")
        print(f"  {'Total':<{col}}  {result.total}")
    else:
        _print_d20_roll_block("[Roll 1]", result.die_roll, result.modifiers, col)
        _print_d20_roll_block("[Roll 2]", result.alt_die_roll or 0, result.modifiers, col)
        rule = "higher" if result.advantage else "lower"
        print(f"\n  Taking {rule}: {result.chosen_total}")


# ---------------------------------------------------------------------------
# Autocomplete
# ---------------------------------------------------------------------------

class _SpellCompleter(Completer):
    """Completes spell names after the 'cast' keyword."""

    def __init__(self, spells: list[str]) -> None:
        self.spells = spells

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not re.match(r'^cast\s+', text, re.IGNORECASE):
            return
        typed = text[text.index(" ") + 1:]
        for spell in self.spells:
            if spell.lower().startswith(typed.lower()):
                yield Completion(spell, start_position=-len(typed))


def _read_line(prompt_str: str, completer: Optional[_SpellCompleter]) -> str:
    """Read a line using prompt_toolkit when a completer is available, else plain input."""
    if completer is not None:
        return pt_prompt(prompt_str, completer=completer)
    return input(prompt_str)


# ---------------------------------------------------------------------------
# Dice roll
# ---------------------------------------------------------------------------

@dataclass
class ShadowdarkRollResult:
    pools: list[tuple[int, int]]  # (count, sides); negative count = subtract
    modifier: int
    rolls: list[int]              # signed individual roll values
    advantage: Optional[bool]     # True=adv, False=dis, None=normal
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


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

def _parse_cast_args(parts: list[str]) -> tuple[str, int, Optional[bool]]:
    """Parse tokens after 'cast': returns (spell_name, situational, advantage)."""
    advantage: Optional[bool] = None
    situational = 0

    if parts and parts[-1].lower() in ("a", "d"):
        advantage = parts[-1].lower() == "a"
        parts = parts[:-1]

    if parts and re.fullmatch(r'[+-]\d+', parts[-1]):
        situational = int(parts[-1])
        parts = parts[:-1]

    spell_name = " ".join(parts)
    return spell_name, situational, advantage


class ShadowdarkSystem(RpgSystem):
    name = "Shadowdark"
    system_slug = "shadowdark"

    def run(self, character: Optional[Character] = None) -> None:
        banner = Banner(build_banner_lines(self.name, character))
        banner.install()
        print("\nEnter dice notation (e.g. D20, 2D6+1, D20-3) or 'q' to quit.")
        print("Append 'a' for advantage or 'd' for disadvantage (e.g. 2D6+1 a, D20 d).")
        prompt_str = "\nWhat do you do Next?> " if character else "\nRoll> "
        completer = _SpellCompleter(get_character_spells(character)) if character else None
        try:
            self._roll_loop(prompt_str, character, completer)
        finally:
            banner.uninstall()

    def _roll_loop(
        self,
        prompt_str: str,
        character: Optional[Character],
        completer: Optional[_SpellCompleter],
    ) -> None:
        while True:
            try:
                raw = _read_line(prompt_str, completer).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if raw.lower() in ("q", "quit", "exit"):
                break
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0].lower()

            # --- check ---
            if cmd == "check":
                if character is None:
                    print("No character loaded — check requires a character sheet.")
                    continue
                check_parts = parts[1:]
                if not check_parts:
                    print("Usage: check <name> [a|d]  (e.g. check per, check wis a)")
                    continue
                check_advantage: Optional[bool] = None
                if check_parts[-1].lower() == "a":
                    check_advantage, check_parts = True, check_parts[:-1]
                elif check_parts[-1].lower() == "d":
                    check_advantage, check_parts = False, check_parts[:-1]
                check_name = " ".join(check_parts).lower()
                if not check_name:
                    print("Usage: check <name> [a|d]  (e.g. check per, check wis a)")
                    continue
                result_c = check(check_name, character, check_advantage)
                if result_c is None:
                    print(f"Unknown check: '{check_name}'. Try a stat (str, wis…) or name (perception, stealth…).")
                else:
                    print_check_result(result_c)
                continue

            # --- cast ---
            if cmd == "cast":
                if character is None:
                    print("No character loaded — cast requires a character sheet.")
                    continue
                spell_name, situational, cast_advantage = _parse_cast_args(parts[1:])
                if not spell_name:
                    print("Usage: cast <spell> [+N|-N] [a|d]  (e.g. cast Cure Wounds +1 a)")
                    continue
                result_cast = cast(spell_name, character, situational, cast_advantage)
                print_cast_result(result_cast)
                continue

            # --- roll (dice notation) ---
            if cmd == "roll" and len(parts) > 1:
                parts = parts[1:]
            suffix = parts[-1].lower() if len(parts) > 1 else ""
            if suffix == "a":
                notation, advantage = " ".join(parts[:-1]), True
            elif suffix == "d":
                notation, advantage = " ".join(parts[:-1]), False
            else:
                notation, advantage = " ".join(parts), None

            result = roll(notation, advantage)
            if result is None:
                print(f"Invalid notation: '{notation}'. Use format like '2D6', 'D20+3', '2D6+1D4-2'.")
            else:
                print_result(notation, result)
