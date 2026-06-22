# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

This project uses a virtualenv at `.venv/`. Always use its binaries:

```bash
.venv/bin/python roll.py
.venv/bin/pytest
.venv/bin/pyright
```

## Running

```bash
.venv/bin/python roll.py
```

Launches an interactive menu to choose a system, then a character, then prompts for dice notation in a loop. Enter `q` to quit at any prompt.

## What it does

Multi-system RPG dice roller with character support. Currently implemented:

- **Star Wars D6** (West End Games): notation `<N>D` or `<N>D+<bonus>` (e.g. `6D`, `4D+2`). First die is the "wild die" — rolls a 6 → explodes (re-roll and add); rolls a 1 → `COMPLICATION` flag. Prints a difficulty reference table at session start.
- **Shadowdark**: notation `<N>D<sides>` or with modifier (e.g. `D20`, `2D6+1`, `D20-3`, `2D6+1D4`). Supports mixed pools (multiple die types summed) and flat modifiers. Negative die counts subtract from the total. Append `a` for advantage or `d` for disadvantage (e.g. `D20 a`, `2D6+1 d`) — rolls twice and takes the higher or lower result.

## Testing

```bash
.venv/bin/pytest                              # run all tests
.venv/bin/pytest tests/test_shadowdark.py    # run a single test file
```

Type checking: `.venv/bin/pyright`

## Code structure

`roll.py` is the entry point — it instantiates all systems, presents `main_menu()` → `character_menu()`, then calls `system.run(character=...)`.

Each RPG system lives in `systems/` and extends `systems/base.py:RpgSystem` (ABC with `name: str`, `system_slug: str`, and `run(character)`):

- `systems/star_wars.py` — `parse_notation`, `roll`, `print_result`, wild die explosion/complication logic, difficulty table
- `systems/shadowdark.py` — `parse_notation`, `roll` (returns `ShadowdarkRollResult`), advantage/disadvantage via `alt_rolls`
- `systems/character.py` — `Character` dataclass (wraps raw YAML `data: dict`) and `load_characters(system_slug)` which reads `data/<system_slug>/*.yaml`
- `systems/banner.py` — `Banner` class (ANSI scroll-region pinned header) and `build_banner_lines(system_name, character)` which renders system, identity, HP/AC, and stat modifiers

**Adding a new system:** implement `RpgSystem` in `systems/<name>.py`, add an instance to `SYSTEMS` in `roll.py`, and optionally add character YAML files under `data/<system_slug>/`.

**Character YAML format** (see `data/shadowdark/urist.yaml` for a full example): top-level keys `meta` (name, system, ancestry, class, level), `combat` (hp, ac_normal, ac_shield), `stats` (str/dex/con/int/wis/cha). The banner reads these sections; unknown keys are ignored.

**Banner behaviour:** `Banner.install()` clears the screen, draws the header, and sets the ANSI scroll region below it so roll output scrolls without touching the header. `Banner.uninstall()` (called via `try/finally`) resets the scroll region and clears the header on exit.
