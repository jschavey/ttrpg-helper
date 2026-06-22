# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running

```bash
python roll.py <notation> [notation ...]
# Examples:
python roll.py 6D
python roll.py 4D+2
python roll.py 3D 5D+1
```

## What it does

This is a Star Wars D6 RPG dice roller (West End Games system). Key rules baked in:

- **Notation**: `<N>D` or `<N>D+<bonus>` (e.g. `6D`, `4D+2`)
- **Special die**: The first die in any pool is the "wild die" — if it rolls a 6, it **explodes** (rolls again and adds the bonus roll to the total). If it rolls a 1, a **COMPLICATION** flag is raised.
- **Output**: Prints each individual die, the total, and any flags (`EXPLODE`, `COMPLICATION`). Also prints a difficulty reference table on every invocation.

## Code structure

Everything lives in `roll.py`:

- `roll_d6()` — single d6 roll
- `parse_notation(notation)` — parses `ND` or `ND+bonus` strings
- `roll_pool(notation)` — main rolling logic; handles wild die explosion and complication detection
- `DIFFICULTY_TABLE` / `print_difficulty_table()` — static difficulty reference printed before each session
