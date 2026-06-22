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

## Code structure

Everything lives in `roll.py`:

- `roll_d6()` — single d6 roll (Star Wars only)
- `parse_notation(notation)` — parses Star Wars `ND` / `ND+bonus` strings
- `roll_pool(notation)` — Star Wars rolling logic; wild die explosion and complication flag
- `DIFFICULTY_TABLE` / `print_difficulty_table()` — static Star Wars difficulty reference
- `parse_shadowdark_notation(notation)` — parses Shadowdark multi-pool notation into `([(count, sides), ...], modifier)`
- `roll_shadowdark(notation)` — Shadowdark rolling logic
- `run_star_wars()` / `run_shadowdark()` — per-system interactive loops
- `main_menu()` — top-level system chooser
