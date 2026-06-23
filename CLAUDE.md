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

`roll.py` is the entry point — instantiates all systems, presents `main_menu()` → `character_menu()` or `story_menu()`, then calls `system.run(character=...)` or `narrate(character)`.

Each RPG system lives in `systems/` and extends `systems/base.py:RpgSystem` (ABC with `name: str`, `system_slug: str`, and `run(character)`):

- `systems/star_wars.py` — `parse_notation`, `roll`, `print_result`, wild die explosion/complication logic, difficulty table
- `systems/shadowdark.py` — `parse_notation`, `roll` (returns `ShadowdarkRollResult`), advantage/disadvantage via `alt_rolls`
- `systems/character.py` — `Character` dataclass (wraps raw YAML `data: dict`) and `load_characters(system_slug)` which reads `data/<system_slug>/*.yaml`
- `systems/banner.py` — `Banner` class (ANSI scroll-region pinned header) and `build_banner_lines(system_name, character)` which renders system, identity, HP/AC, and stat modifiers
- `systems/narrator.py` — `narrate(character)` builds a prompt from the full character YAML, calls an LLM, and streams the response to stdout

**Adding a new system:** implement `RpgSystem` in `systems/<name>.py`, add an instance to `SYSTEMS` in `roll.py`, and optionally add character YAML files under `data/<system_slug>/`.

## Character YAML format

See `data/shadowdark/urist.yaml` for a full example. Top-level keys:

- `meta` — name, system, ancestry, class, level, and `status: "finished" | "ongoing"` (used by the story menu to group characters; defaults to `"ongoing"` if absent)
- `combat` — hp, ac_normal, ac_shield
- `stats` — str/dex/con/int/wis/cha
- `personality_and_hooks`, `campaign_context` — freeform text blocks consumed by the narrator; unknown keys are ignored by the banner

**Banner behaviour:** `Banner.install()` clears the screen, draws the header, and sets the ANSI scroll region below it so roll output scrolls without touching the header. `Banner.uninstall()` (called via `try/finally`) resets the scroll region and clears the header on exit.

## Narrator / "Relive an epic story"

The main menu's "Relive an epic story" option calls `story_menu()` in `roll.py`, which groups all characters across all systems by their `meta.status` field and lets the user pick one. The selected character's full YAML is serialised and sent to an LLM for cinematic re-narration.

**LLM configuration** lives in `llm_config.yaml` (gitignored — copy from `llm_config.example.yaml`). Supported providers:

- `anthropic` — uses the `anthropic` SDK; reads the API key from `ANTHROPIC_API_KEY` (or the env var named in `api_key_env`)
- `openai_compatible` — uses the `openai` SDK; set `base_url` for LM Studio or any OpenAI-compatible endpoint; `api_key` can be set directly in the config file

The narrator prompt instructs the LLM to treat stat scores as ground truth — low INT means genuine blundering, not arrogance; the gap between a character's self-image and their actual ability scores is treated as primary narrative material.
