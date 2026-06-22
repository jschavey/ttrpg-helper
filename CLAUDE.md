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
- **Shadowdark**: stub only, not yet implemented.

## Code structure

Everything lives in `roll.py`:

- `roll_d6()` — single d6 roll
- `parse_notation(notation)` — parses `ND` or `ND+bonus` strings
- `roll_pool(notation)` — main rolling logic; handles wild die explosion and complication
- `DIFFICULTY_TABLE` / `print_difficulty_table()` — static difficulty reference
- `run_star_wars()` / `run_shadowdark()` — per-system interactive loops
- `main_menu()` — top-level system chooser
