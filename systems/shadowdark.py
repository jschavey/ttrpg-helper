import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import Completer, Completion, WordCompleter

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
# Attack
# ---------------------------------------------------------------------------

@dataclass
class AttackResult:
    weapon_name: str
    weapon_type: str
    stat_key: str
    stat_value: int
    die_roll: int
    modifiers: list[tuple[str, int]]
    advantage: Optional[bool]
    alt_die_roll: Optional[int]
    backstab: bool = False
    thrown: bool = False

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


def parse_attack(parts: list[str]) -> tuple[str, bool, bool, Optional[bool], int]:
    """Parse tokens after 'att': (weapon_name, thrown, backstab, advantage, situational)."""
    parts = list(parts)
    thrown = False
    backstab = False
    advantage: Optional[bool] = None
    situational = 0

    if parts and parts[0].lower() == "throw":
        thrown = True
        parts = parts[1:]
    elif parts and parts[0].lower() == "backstab":
        backstab = True
        parts = parts[1:]

    # Consume trailing a/d and/or +N in any order (handles "sword a +1" and "sword +1 a")
    for _ in range(2):
        if parts and parts[-1].lower() in ("a", "d"):
            advantage = parts[-1].lower() == "a"
            parts = parts[:-1]
        elif parts and re.fullmatch(r'[+-]\d+', parts[-1]):
            situational = int(parts[-1])
            parts = parts[:-1]

    weapon_name = " ".join(parts)
    return weapon_name, thrown, backstab, advantage, situational


def roll_attack(
    weapon_name: str,
    character: "Character",
    thrown: bool = False,
    backstab: bool = False,
    advantage: Optional[bool] = None,
    situational: int = 0,
    both_flags: bool = False,
) -> AttackResult:
    """Roll an attack. Raises ValueError on invalid input."""
    if both_flags:
        raise ValueError("Cannot combine advantage and disadvantage.")

    weapons: list[dict] | None = character.data.get("weapons")
    if not weapons:
        raise ValueError("No weapons defined on this character sheet.")

    weapon = next(
        (w for w in weapons if w["name"].lower() == weapon_name.lower()),
        None,
    )
    if weapon is None:
        available = ", ".join(w["name"] for w in weapons)
        raise ValueError(f"Unknown weapon: {weapon_name}. Available: {available}.")

    if thrown and not weapon.get("throwable", False):
        raise ValueError(f"{weapon['name']} is not throwable.")

    cls = character.data.get("meta", {}).get("class", "").lower()
    if backstab and cls != "thief":
        raise ValueError("Backstab is a Thief-only ability.")

    if backstab:
        advantage = True

    weapon_type = weapon["type"]
    stat_key = "str" if weapon_type == "melee" or thrown else "dex"
    stat_value = character.data.get("stats", {}).get(stat_key, 10)
    stat_mod = (stat_value - 10) // 2

    modifiers: list[tuple[str, int]] = [
        (f"{stat_key.upper()} {stat_value:+d}", stat_mod),
    ]
    if situational:
        modifiers.append((f"Situational {situational:+d}", situational))

    die_roll = random.randint(1, 20)
    alt_die_roll = random.randint(1, 20) if advantage is not None else None

    return AttackResult(
        weapon_name=weapon["name"],
        weapon_type=weapon_type,
        stat_key=stat_key,
        stat_value=stat_value,
        die_roll=die_roll,
        modifiers=modifiers,
        advantage=advantage,
        alt_die_roll=alt_die_roll,
        backstab=backstab,
        thrown=thrown,
    )


def print_attack_result(result: AttackResult) -> None:
    mode = "Backstab" if result.backstab else ("Thrown" if result.thrown else "Attack")
    adv_label = " (advantage)" if result.advantage is True else " (disadvantage)" if result.advantage is False else ""
    print(f"\n⚔  {mode} — {result.weapon_name.title()} ({result.weapon_type}){adv_label}")
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

class _CommandCompleter(Completer):
    """Completes arguments for 'cast', 'check', 'roll', and 'att' commands."""

    def __init__(self, spells: list[str], character: Optional["Character"] = None) -> None:
        self.spells = spells
        self.character = character
        self._check_options = sorted(CHECKS.keys())
        self._roll_options = ["init"]

    def _weapon_names(self, throwable_only: bool = False) -> list[str]:
        if self.character is None:
            return []
        weapons: list[dict] = self.character.data.get("weapons", []) or []
        if throwable_only:
            return [w["name"] for w in weapons if w.get("throwable")]
        return [w["name"] for w in weapons]

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # --- att command ---
        m_att = re.match(r'^att\s+', text, re.IGNORECASE)
        if m_att:
            typed = text[m_att.end():]
            cls = ""
            if self.character:
                cls = self.character.data.get("meta", {}).get("class", "").lower()

            # After "att throw "
            m_throw = re.match(r'^throw\s+', typed, re.IGNORECASE)
            if m_throw:
                sub = typed[m_throw.end():]
                for name in self._weapon_names(throwable_only=True):
                    if name.lower().startswith(sub.lower()):
                        yield Completion(name, start_position=-len(sub))
                return

            # After "att backstab "
            m_back = re.match(r'^backstab\s+', typed, re.IGNORECASE)
            if m_back:
                sub = typed[m_back.end():]
                for name in self._weapon_names():
                    if name.lower().startswith(sub.lower()):
                        yield Completion(name, start_position=-len(sub))
                return

            # After weapon name — offer a, d, modifiers
            weapon_names = self._weapon_names()
            for wname in weapon_names:
                if typed.lower().startswith(wname.lower() + " "):
                    sub = typed[len(wname) + 1:]
                    for opt in ["a", "d", "+1", "-1", "+2", "-2"]:
                        if opt.startswith(sub):
                            yield Completion(opt, start_position=-len(sub))
                    return

            # First token after "att "
            for opt in (["throw"] + (["backstab"] if cls == "thief" else []) + weapon_names):
                if opt.lower().startswith(typed.lower()):
                    yield Completion(opt, start_position=-len(typed))
            return

        m = re.match(r'^(cast|check|roll)\s+', text, re.IGNORECASE)
        if not m:
            return
        cmd = m.group(1).lower()
        typed = text[m.end():]
        if cmd == "cast":
            options = self.spells
        elif cmd == "check":
            options = self._check_options
        else:  # roll
            options = self._roll_options
        for option in options:
            if option.lower().startswith(typed.lower()):
                yield Completion(option, start_position=-len(typed))


def _read_line(prompt_str: str, completer: Optional[_CommandCompleter]) -> str:
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
# Character Creation
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent.parent / "data"
_LLM_CONFIG_PATH = Path(__file__).parent.parent / "llm_config.yaml"

ANCESTRIES = ["Human", "Elf", "Dwarf", "Halfling", "Half-Orc"]
CLASSES = ["Fighter", "Priest", "Thief", "Wizard"]
_GENDER_OPTIONS = ["Male", "Female", "Freeform", "Random"]

_ANCESTRY_LANGUAGES: dict[str, list[str]] = {
    "Human": [],
    "Elf": ["Elvish", "Sylvan"],
    "Dwarf": ["Dwarvish"],
    "Halfling": [],
    "Half-Orc": ["Orcish"],
    "Goblin": ["Goblin"],
}

_HIT_DICE: dict[str, int] = {
    "fighter": 8,
    "priest": 6,
    "thief": 4,
    "wizard": 4,
}

_BACKSTORY_TABLE = [
    ("Urchin", "You grew up in the merciless streets of a large city"),
    ("Wanted", "There's a price on your head, but you have allies"),
    ("Cult Initiate", "You know blasphemous secrets and rituals"),
    ("Thieve's Guild", "You have connections, contacts, and debts"),
    ("Banished", "Your people cast you out for supposed crimes"),
    ("Orphaned", "An unusual guardian rescued and raised you"),
    ("Wizard's Apprentice", "You have a knack and eye for magic"),
    ("Jeweler", "You can easily appraise value and authenticity"),
    ("Herbalist", "You know plants, medicines, and poisons"),
    ("Barbarian", "You left the horde, but it never quite left you"),
    ("Mercenary", "You fought friend and foe alike for your coin"),
    ("Sailor", "Pirate, privateer, or merchant — the seas are yours"),
    ("Acolyte", "You're well trained in religious rites and doctrines"),
    ("Soldier", "You served as a fighter in an organized army"),
    ("Ranger", "The woods and wilds are your true home"),
    ("Scout", "You survived on stealth, observation, and speed"),
    ("Minstrel", "You've traveled far with your charm and talent"),
    ("Scholar", "You know much about ancient history and lore"),
    ("Noble", "A famous name has opened many doors for you"),
    ("Chirurgeon", "You know anatomy, surgery, and first aid"),
]

_AUTO_PRONOUNS: dict[str, str] = {
    "male": "he/him",
    "female": "she/her",
    "non-binary": "they/them",
}


def _load_llm_config() -> dict[str, Any]:
    if not _LLM_CONFIG_PATH.exists():
        return {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}
    with open(_LLM_CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def _unique_yaml_path(name: str) -> Path:
    base = _slugify(name)
    target = _DATA_DIR / "shadowdark" / f"{base}.yaml"
    if not target.exists():
        return target
    i = 2
    while True:
        candidate = _DATA_DIR / "shadowdark" / f"{base}_{i}.yaml"
        if not candidate.exists():
            return candidate
        i += 1


def _prompt_choice(prompt_str: str, options: list[str]) -> str:
    """Prompt with autocomplete until a valid option is entered. q/ctrl-C aborts."""
    completer = WordCompleter(options, ignore_case=True)
    lower_map = {o.lower(): o for o in options}
    while True:
        try:
            val = pt_prompt(prompt_str, completer=completer).strip()
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt
        if val.lower() in ("q", "quit"):
            raise KeyboardInterrupt
        if val.lower() in lower_map:
            return lower_map[val.lower()]
        print(f"  Please choose from: {', '.join(options)}")


def _prompt_freetext(prompt_str: str) -> str:
    """Prompt for non-empty free text. q/ctrl-C aborts."""
    while True:
        try:
            val = pt_prompt(prompt_str).strip()
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt
        if val.lower() in ("q", "quit"):
            raise KeyboardInterrupt
        if val:
            return val
        print("  Cannot be empty.")


def _roll_stats() -> dict[str, int]:
    stat_keys = ["str", "dex", "con", "int", "wis", "cha"]
    stat_labels = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    attempt = 0
    while True:
        attempt += 1
        roll_sets = [[random.randint(1, 6) for _ in range(3)] for _ in stat_keys]
        totals = [sum(s) for s in roll_sets]
        if max(totals) >= 14:
            print(f"  Stats (attempt {attempt}):")
            for label, dice_set, total in zip(stat_labels, roll_sets, totals):
                marker = "  ✓ (≥14)" if total >= 14 else ""
                print(f"    {label}: rolled 3d6 → {dice_set} = {total}{marker}")
            return dict(zip(stat_keys, totals))
        else:
            print(f"  Stats (attempt {attempt}): {' '.join(str(s) for s in roll_sets)} — no stat ≥ 14, rerolling...")


def _roll_gold() -> int:
    dice = [random.randint(1, 6) for _ in range(2)]
    total = sum(dice) * 5
    print(f"  Gold: rolled 2d6 → {dice} × 5 = {total}gp")
    return total


def _roll_backstory() -> tuple[str, str]:
    roll = random.randint(1, 20)
    title, detail = _BACKSTORY_TABLE[roll - 1]
    print(f"  Backstory: rolled 1d20 → {roll} = {title}")
    return title, detail


def _roll_hp(cls: str, con: int, ancestry: str) -> int:
    hit_die = _HIT_DICE.get(cls.lower(), 6)
    con_mod = (con - 10) // 2
    is_dwarf = ancestry.lower() == "dwarf"
    roll1 = random.randint(1, hit_die)
    if is_dwarf:
        roll2 = random.randint(1, hit_die)
        chosen = max(roll1, roll2)
        hp = max(1, chosen + con_mod + 2)
        print(f"  HP: rolled 1d{hit_die} ({cls}, Dwarf advantage) → [{roll1}, {roll2}], took {chosen} + CON mod ({con_mod:+d}) + Dwarf +2 = {hp}")
    else:
        hp = max(1, roll1 + con_mod)
        print(f"  HP: rolled 1d{hit_die} ({cls}) → {roll1} + CON mod ({con_mod:+d}) = {hp}")
    return hp


def _llm_generate_name(ancestry: str, gender: str) -> Optional[str]:
    config = _load_llm_config()
    provider = config.get("provider", "anthropic")
    prompt = (
        f"Generate a single fantasy name for a {gender} {ancestry} character "
        f"in the Shadowdark RPG setting. Reply with only the name, nothing else."
    )
    try:
        if provider == "anthropic":
            import anthropic
            api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
            api_key = os.environ.get(api_key_env)
            client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
            msg = client.messages.create(
                model=config.get("model", "claude-haiku-4-5-20251001"),
                max_tokens=32,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        elif provider == "openai_compatible":
            from openai import OpenAI
            api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
            api_key = config.get("api_key") or os.environ.get(api_key_env) or "local"
            base_url = config.get("base_url")
            client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=config.get("model", "gpt-4o-mini"),
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            msg = resp.choices[0].message
            text = (msg.content or "").strip()
            # Qwen3 thinking models may wrap the answer in <think>...</think>;
            # strip those tags and take whatever follows.
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            # If still empty, check reasoning_content (some LM Studio builds expose it).
            if not text:
                reasoning = getattr(msg, "reasoning_content", None) or ""
                text = reasoning.strip()
            return text or None
    except Exception as e:
        print(f"  LLM error: {e}")
    return None


def create_character() -> Optional[Character]:
    """Interactive Shadowdark character creation. Returns the new Character or None if aborted."""
    print("\n=== New Shadowdark Character ===\n")
    try:
        # Step 1: Ancestry
        print("Step 1: Ancestry")
        ancestry_choice = _prompt_choice("  Ancestry> ", ANCESTRIES + ["Random"])
        if ancestry_choice == "Random":
            ancestry = random.choice(ANCESTRIES)
            print(f"  → Rolled: {ancestry}")
        else:
            ancestry = ancestry_choice
        print(f"  Ancestry: {ancestry}\n")

        # Step 2: Gender + pronouns
        print("Step 2: Gender")
        gender_choice = _prompt_choice("  Gender> ", _GENDER_OPTIONS)
        if gender_choice == "Random":
            gender = random.choice(["Male", "Female", "Non-binary"])
            print(f"  → Rolled: {gender}")
        elif gender_choice == "Freeform":
            gender = _prompt_freetext("  Enter gender> ")
        else:
            gender = gender_choice

        pronouns = _AUTO_PRONOUNS.get(gender.lower())
        if pronouns is None:
            print(f"  What pronouns does {gender} use?")
            pronouns = _prompt_freetext("  Pronouns> ")
        print(f"  Gender: {gender}  ({pronouns})\n")

        # Step 3: Name
        print("Step 3: Name  (type 'random' for an LLM-generated name)")
        name: Optional[str] = None
        while name is None:
            raw = _prompt_freetext("  Name> ")
            if raw.lower() == "random":
                print("  Asking the LLM for a name...")
                generated = _llm_generate_name(ancestry, gender)
                if generated is None:
                    print("  LLM unavailable — please enter a name manually.")
                    continue
                print(f"  Suggested: {generated}")
                while True:
                    confirm = _prompt_choice("  Accept? > ", ["yes", "no", "custom"])
                    if confirm == "yes":
                        name = generated
                        break
                    elif confirm == "no":
                        print("  Asking the LLM for another name...")
                        generated = _llm_generate_name(ancestry, gender)
                        if generated is None:
                            print("  LLM unavailable — please enter a name manually.")
                            break
                        print(f"  Suggested: {generated}")
                    else:
                        name = _prompt_freetext("  Enter custom name> ")
                        break
            else:
                name = raw
        print(f"  Name: {name}\n")

        # Rolls
        print("Rolling stats (3d6 each, reroll all if no stat ≥ 14):")
        stats = _roll_stats()

        print("\nRolling starting gold:")
        gold = _roll_gold()

        print("\nRolling backstory:")
        backstory_title, backstory_detail = _roll_backstory()

        # Languages
        languages: list[str] = ["Common"] + _ANCESTRY_LANGUAGES.get(ancestry, [])
        print(f"\nLanguages: {', '.join(languages)}")
        if ancestry == "Human":
            print("  Humans may add one additional language. Edit your character YAML to add it to the languages list when you have the options.")

        # AC
        dex_mod = (stats["dex"] - 10) // 2
        ac_normal = 10 + dex_mod
        ac_shield = ac_normal + 2
        print(f"\nAC: {ac_normal} (normal), {ac_shield} (with shield)  [DEX mod: {dex_mod:+d}]")

        # Build and write initial YAML (no class/HP yet)
        char_data: dict[str, Any] = {
            "meta": {
                "name": name,
                "system": "shadowdark",
                "ancestry": ancestry,
                "class": "",
                "level": 1,
                "status": "ongoing",
                "gender": gender,
                "pronouns": pronouns,
            },
            "combat": {
                "hp": 0,
                "ac_normal": ac_normal,
                "ac_shield": ac_shield,
            },
            "stats": stats,
            "gold": gold,
            "languages": languages,
            "backstory": backstory_title,
            "backstory_detail": backstory_detail,
            "weapons": [],
            "spells": {},
            "talents": [],
            "personality_and_hooks": "",
            "campaign_context": "",
        }

        yaml_path = _unique_yaml_path(name)
        try:
            with open(yaml_path, "w") as f:
                yaml.dump(char_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"\n  Saved to {yaml_path.name}")
        except OSError as e:
            print(f"\n  Error writing character file: {e}")
            return None

        # Step 4: Class
        print("\nStep 4: Class")
        class_choice = _prompt_choice("  Class> ", CLASSES + ["Random"])
        if class_choice == "Random":
            cls = random.choice(CLASSES)
            print(f"  → Rolled: {cls}")
        else:
            cls = class_choice
        print(f"  Class: {cls}\n")

        # Roll HP now that class is known
        print("Rolling HP:")
        hp = _roll_hp(cls, stats["con"], ancestry)

        # Update YAML with class and HP
        char_data["meta"]["class"] = cls
        char_data["combat"]["hp"] = hp
        try:
            with open(yaml_path, "w") as f:
                yaml.dump(char_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        except OSError as e:
            print(f"\n  Error updating character file: {e}")

        print(f"\n✓ {name} the {ancestry} {cls} is ready!\n")
        return Character(name=name, source_file=yaml_path, data=char_data)

    except KeyboardInterrupt:
        print("\n  Character creation cancelled.")
        return None


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
        completer = _CommandCompleter(get_character_spells(character), character=character) if character else None
        try:
            self._roll_loop(prompt_str, character, completer, banner)
        finally:
            banner.uninstall()

    def _roll_loop(
        self,
        prompt_str: str,
        character: Optional[Character],
        completer: Optional[_CommandCompleter],
        banner: Optional[Banner] = None,
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

            # --- att ---
            if cmd == "att":
                if character is None:
                    print("No character loaded — att requires a character sheet.")
                    continue
                att_parts = parts[1:]
                if not att_parts:
                    print("Usage: att [throw|backstab] <weapon> [a|d] [+N|-N]")
                    continue
                weapon_name, thrown, backstab, att_adv, situational = parse_attack(att_parts)
                both_flags = att_adv is not None and backstab  # backstab overrides d; only flag a+d explicitly
                # Check for explicit a and d tokens together
                lower_parts = [p.lower() for p in att_parts]
                if "a" in lower_parts and "d" in lower_parts:
                    print("Cannot combine advantage and disadvantage.")
                    continue
                try:
                    att_result = roll_attack(
                        weapon_name, character,
                        thrown=thrown, backstab=backstab,
                        advantage=att_adv, situational=situational,
                    )
                except ValueError as exc:
                    print(str(exc))
                    continue
                print_attack_result(att_result)
                continue

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
                if banner is not None:
                    banner.redraw(build_banner_lines(self.name, character))
                continue

            # --- roll init ---
            if cmd == "roll" and len(parts) > 1 and parts[1].lower() == "init":
                if character is None:
                    print("No character loaded — initiative requires a character sheet.")
                    continue
                init_advantage: Optional[bool] = None
                if len(parts) > 2:
                    flag = parts[2].lower()
                    if flag == "a":
                        init_advantage = True
                    elif flag == "d":
                        init_advantage = False
                result_init = check("dex", character, init_advantage)
                if result_init is None:
                    print("Character is missing DEX stat.")
                else:
                    result_init.check_name = "Initiative"
                    print_check_result(result_init)
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
