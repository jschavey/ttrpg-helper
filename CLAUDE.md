# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running

```bash
python roll.py
```

Launches an interactive menu to choose a system, then prompts for dice notation in a loop. Enter `q` to quit at any prompt.

## What it does

Multi-system RPG dice roller. Currently implemented:

- **Star Wars D6** (West End Games): notation `<N>D` or `<N>D+<bonus>` (e.g. `6D`, `4D+2`). First die is the "wild die" — rolls a 6 → explodes (re-roll and add); rolls a 1 → `COMPLICATION` flag. Prints a difficulty reference table at session start.
- **Shadowdark**: notation `<N>D<sides>` or with modifier (e.g. `D20`, `2D6+1`, `D20-3`, `2D6+1D4`). Supports mixed pools (multiple die types summed) and flat modifiers. Negative die counts subtract from the total. Append `a` for advantage or `d` for disadvantage (e.g. `D20 a`, `2D6+1 d`) — rolls twice and takes the higher or lower result.

## Testing

```bash
pytest                              # run all tests
pytest tests/test_shadowdark.py    # run a single test file
```

Type checking: `pyright`

## Code structure

`roll.py` is the entry point — it instantiates all systems and runs `main_menu()`.

Each RPG system lives in `systems/` and extends `systems/base.py:RpgSystem` (an ABC with a `name: str` attribute and a `run()` method):

- `systems/star_wars.py` — parsing (`parse_notation`), rolling (`roll_pool`), wild die explosion/complication logic, difficulty table
- `systems/shadowdark.py` — multi-pool notation parsing (`parse_shadowdark_notation`), rolling (`roll_shadowdark`), advantage/disadvantage

To add a new system: implement `RpgSystem` in a new `systems/<name>.py`, then add an instance to the `SYSTEMS` list in `roll.py`.
