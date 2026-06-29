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

Launches an interactive menu: choose a system → choose a character → enter dice notation in a loop. Enter `q` to quit at any prompt.

## Testing

```bash
.venv/bin/pytest                              # run all tests
.venv/bin/pytest tests/test_shadowdark.py    # run a single test file
.venv/bin/pytest -k "test_name"              # run a single test by name
```

Type checking: `.venv/bin/pyright`

## Code structure

`roll.py` is the entry point — instantiates all systems in `SYSTEMS`, presents `main_menu()` → `character_menu()` or `story_menu()`, then calls `system.run(character=...)` or `narrate(character)`.

Each RPG system lives in `systems/` and extends `systems/base.py:RpgSystem` (ABC with `name: str`, `system_slug: str`, and `run(character)`):

- `systems/star_wars_d6.py` — canonical WEG Star Wars D6 system: `parse_notation`, `roll`, `print_result`, wild die explosion/complication logic, wound state tracking, pinned difficulty table in the banner
- `systems/shadowdark.py` — `parse_notation`, `roll` (returns `ShadowdarkRollResult`), advantage/disadvantage via `alt_rolls`, HP tracking with `hp +N / hp -N`
- `systems/character.py` — `Character` dataclass (wraps raw YAML `data: dict`) and `load_characters(system_slug)` which reads `data/<system_slug>/*.yaml`. Name is resolved from `meta.name` first, then `character_info.name`, then the filename stem.
- `systems/banner.py` — `Banner` class (ANSI scroll-region pinned header) and `build_banner_lines(system_name, character)` for Shadowdark-schema characters. `Banner.install()` clears the screen and sets the ANSI scroll region; `Banner.uninstall()` (called via `try/finally`) resets it.
- `systems/narrator.py` — `narrate(character)` builds a prompt from the full character YAML, calls an LLM, and streams the response to stdout

**Adding a new system:** implement `RpgSystem` in `systems/<name>.py`, add an instance to `SYSTEMS` in `roll.py`, and add character YAML files under `data/<system_slug>/`.

## Shadowdark in-game commands

When a character is loaded, `_roll_loop` in `systems/shadowdark.py` dispatches these commands in addition to raw dice notation:

| Command | Syntax | Notes |
|---------|--------|-------|
| `check` | `check <name> [a\|d]` | Stat or named check (perception, stealth…); a=advantage, d=disadvantage |
| `cast` | `cast <spell> [+N\|-N] [a\|d]` | Applies class spellcasting stat mod + talent bonuses |
| `att` | `att [throw\|backstab] <weapon> [a\|d] [+N\|-N]` | Melee→STR, ranged→DEX, thrown→STR; backstab is Thief-only (auto-advantage) |
| `hp` | `hp +N` / `hp -N` | Updates session HP and persists to the YAML file |
| `roll init` | `roll init [a\|d]` | DEX check labelled "Initiative" |
| `roll` | `roll <notation> [a\|d]` | Raw dice: `D20`, `2D6+1`, `D20-3` etc. |

Stat modifier formula throughout: `(stat_value - 10) // 2`.

## Character YAML schemas

Two schemas exist — each system reads its own:

**Shadowdark** (`data/shadowdark/*.yaml`) — see `urist.yaml` for a full example:
- `meta` — name, system, ancestry, class, level, `status: "finished" | "ongoing"` (story menu grouping; defaults to `"ongoing"`)
- `combat` — hp, ac_normal, ac_shield
- `stats` — str/dex/con/int/wis/cha
- `weapons` *(optional)* — list of `{name, type: melee|ranged, throwable?: bool}`; required for `att` command; omitting the key is safe
- `spells` — dict of tier lists (`tier_1: [...]`); consumed by `cast` autocomplete
- `talents` — list of strings; `"+1 to priest spellcasting checks"` is the only talent text currently parsed
- `personality_and_hooks`, `campaign_context` — freeform text consumed by the narrator

**Star Wars D6 WEG** (`data/star-wars-d6/*.yaml`) — see `C4V3.yaml` for a full example:
- `character_info` — name, type, aliases, appearance, etc.
- `attributes_and_skills` — keyed by attribute name (DEXTERITY, KNOWLEDGE, MECHANICAL, PERCEPTION, STRENGTH, TECHNICAL), each with a `base` die code and a `skills` dict
- `meta_game` — force_points, character_points, wounds (text wound state)
- `backstory`, `equipment`, `session_notes` — freeform; consumed by the narrator

The banner for Star Wars D6 is built by `star_wars_d6.build_banner_lines()` (not `systems/banner.py`) and always includes the pinned difficulty table.

## Narrator / "Relive an epic story"

The main menu's "Relive an epic story" option calls `story_menu()` in `roll.py`, which groups all characters across all systems by their status field (`meta.status` for Shadowdark, defaults to `"ongoing"` if absent) and lets the user pick one. The selected character's full YAML is serialised and sent to an LLM for cinematic re-narration.

**LLM configuration** lives in `llm_config.yaml` (gitignored — copy from `llm_config.example.yaml`). Supported providers:

- `anthropic` — uses the `anthropic` SDK; reads the API key from `ANTHROPIC_API_KEY` (or the env var named in `api_key_env`)
- `openai_compatible` — uses the `openai` SDK; set `base_url` for LM Studio or any OpenAI-compatible endpoint; `api_key` can be set directly in the config file

The narrator prompt instructs the LLM to treat stat scores as ground truth — the gap between a character's self-image and their actual ability scores is treated as primary narrative material.
