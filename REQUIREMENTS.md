# Attack Roll Feature — Shadowdark System

## Overview

Add an `att` command to the Shadowdark system that resolves weapon attack rolls against the character's equipped weapons. Supports advantage/disadvantage, situational modifiers, and a Thief-only backstab mode.

---

## Character Sheet Changes

Add a `weapons` list to Shadowdark character YAML. Each entry is a mapping with these fields:

| Field        | Type    | Required | Values                     | Description                          |
|--------------|---------|----------|----------------------------|--------------------------------------|
| `name`       | string  | yes      | any                        | Weapon name shown in autocomplete    |
| `type`       | string  | yes      | `melee` \| `ranged`        | Determines which stat mod is applied |
| `throwable`  | boolean | no       | `true` \| `false`          | Defaults to `false`                  |

### Example YAML

```yaml
weapons:
  - name: dagger
    type: melee
    throwable: true
  - name: shortsword
    type: melee
    throwable: false
  - name: shortbow
    type: ranged
    throwable: false
```

Existing characters without a `weapons` key must still load without error; the `att` command should print a helpful message if no weapons are defined.

---

## Command Syntax

```
att [throw] <weapon> [a|d] [+N|-N]
```

| Token      | Required | Description                                                    |
|------------|----------|----------------------------------------------------------------|
| `throw`    | no       | Keyword; restricts weapon choices to throwable weapons only    |
| `<weapon>` | yes      | Weapon name from the character sheet (case-insensitive)        |
| `a` / `d`  | no       | Advantage (`a`) or Disadvantage (`d`)                          |
| `+N` / `-N`| no       | Integer situational modifier applied to the roll               |

### Examples

```
att sword
att sword a
att sword d +1
att sword a -2
att throw dagger
att throw dagger a +1
att bow d
att backstab dagger
att backstab dagger a
```

---

## Autocomplete (prompt_toolkit)

Extend the existing `Completer` in `systems/shadowdark.py`:

- After `att `, complete with all weapon names **plus** `throw` and (for Thieves) `backstab`.
- After `att throw `, complete with only throwable weapon names.
- After `att backstab `, complete with all weapon names (Thief class only; otherwise `backstab` is not offered).
- After a weapon name, offer `a`, `d`, and common modifier tokens (`+1`, `-1`, `+2`, `-2`).

---

## Roll Mechanics

### Base Roll

Roll **1d20**.

### Attribute Modifier

Apply a stat modifier based on weapon type (same modifier formula already used for checks):

| Weapon type            | Stat used   |
|------------------------|-------------|
| `melee`                | STR modifier |
| `ranged`               | DEX modifier |
| `melee` + `throw` flag | STR modifier |

Modifier = `(stat_value - 10) // 2` (standard Shadowdark/D20 formula).

### Advantage / Disadvantage

Roll two d20s; take the higher (advantage) or lower (disadvantage). Same implementation pattern as existing `ShadowdarkRollResult` alt-roll logic.

### Situational Modifier

An optional integer (`+N` or `-N`) added on top of the stat modifier.

### Backstab (Thief only)

- Keyword `backstab` replaces the weapon-type word in the command.
- Available **only** when `meta.class` (case-insensitive) equals `"thief"`.
- Automatically grants **advantage** on the roll (regardless of whether `a` is typed).
- If the player also types `d`, ignore it and apply advantage (backstab overrides).
- Label the output clearly as a backstab roll.
- If a non-Thief types `backstab`, print an error and do not roll.

---

## Output Format

Follow the existing Shadowdark print conventions (coloured ANSI output, banner stays pinned). Suggested fields to display:

```
⚔  Attack — Shortsword (melee)
   Roll:     14  (d20)
   STR mod:  +1
   Situational: +1
   ─────────────
   Total:    16
```

For advantage/disadvantage, show both rolls and indicate which was chosen (same pattern as existing check output).

---

## Error Handling

| Situation                              | Behaviour                                              |
|----------------------------------------|--------------------------------------------------------|
| No `weapons` key on character          | Print "No weapons defined on this character sheet."    |
| Weapon name not found                  | Print "Unknown weapon: <name>. Available: <list>."     |
| `throw` used with non-throwable weapon | Print "<weapon> is not throwable."                     |
| `backstab` used by non-Thief           | Print "Backstab is a Thief-only ability."              |
| `a` and `d` both present              | Print "Cannot combine advantage and disadvantage."     |

---

## Files to Change

| File                              | Change                                                                     |
|-----------------------------------|----------------------------------------------------------------------------|
| `systems/shadowdark.py`           | Add `AttackResult` dataclass, `parse_attack`, `roll_attack`, `print_attack_result`, extend completer and `run()` dispatch |
| `data/shadowdark/*.yaml`          | Add `weapons` list to each character that should support attack rolling     |
| `tests/test_shadowdark.py`        | Unit tests for parse, roll, modifier, backstab, error paths                |

No changes required to `systems/base.py`, `systems/character.py`, or `roll.py`.

---

# Character Creation — Shadowdark System

## Overview

Add a "Create new character" option to the Shadowdark character menu. The flow guides the user through ancestry selection and name entry, then writes a new YAML file to `data/shadowdark/`.

---

## Flow

```
Character menu
  └─ [Create new character]
       ├─ Step 1: Ancestry
       ├─ Step 2: Gender
       ├─ Step 3: Name
       │    └─ (roll stats → roll gold → roll backstory → assign languages → write YAML)
       └─ Step 4: Class
            └─ (roll HP → update YAML → return to character menu with new character loaded)
```

The file is written to disk after Step 2 with everything that can be resolved without a class. Step 3 adds class and HP, then updates the same file.

### Roll Transparency

Every die roll made during character creation must be printed to the terminal immediately when it occurs, showing the individual dice values and the final result. This allows integrity auditing of the generated character. Example format:

```
STR: rolled 3d6 → [4, 3, 6] = 13
DEX: rolled 3d6 → [6, 6, 5] = 17  ✓ (14+ threshold met)
...
Gold: rolled 2d6 → [3, 5] × 5 = 40gp
Backstory: rolled 1d20 → 12 = Sailor
HP: rolled 1d6 (Priest) → 4 + CON mod (1) = 5
```

For rerolled stat blocks (no stat ≥ 14), print each failed set before the next attempt:

```
Stats (attempt 1): [4, 3, 6] [2, 5, 1] [3, 4, 2] [1, 2, 3] [4, 3, 2] [2, 1, 4] — no stat ≥ 14, rerolling...
```

---

## Step 1: Ancestry

Prompt the user to choose an ancestry from:

| Choice      | Result                          |
|-------------|----------------------------------|
| `Human`     | ancestry set to `Human`         |
| `Elf`       | ancestry set to `Elf`           |
| `Dwarf`     | ancestry set to `Dwarf`         |
| `Halfling`  | ancestry set to `Halfling`      |
| `Half-Orc`  | ancestry set to `Half-Orc`      |
| `Random`    | system randomly selects one of the five ancestries above |

Use `prompt_toolkit` with autocomplete on the six options (case-insensitive). Re-prompt on invalid input. Display the resolved ancestry before moving to the next step.

---

## Step 2: Gender

Prompt the user to choose a gender:

| Choice     | Result                                                                          |
|------------|---------------------------------------------------------------------------------|
| `Male`     | gender set to `Male`                                                            |
| `Female`   | gender set to `Female`                                                          |
| `Freeform` | player is prompted to type any string; that value is stored as-is              |
| `Random`   | system randomly selects from Male, Female, or Non-binary (they/them)            |

Use `prompt_toolkit` with autocomplete on the four options (case-insensitive). Re-prompt on invalid input. For `Freeform`, re-prompt if the player submits an empty string. Display the resolved gender before moving to the next step. Store as `meta.gender` in the YAML.

### Pronouns

Pronouns are derived from the resolved gender value:

| Resolved gender | Pronouns       |
|-----------------|----------------|
| Male            | he/him         |
| Female          | she/her        |
| Non-binary      | they/them      |
| Any other value | prompt the player to enter pronouns as free text (re-prompt if empty) |

Store as `meta.pronouns` in the YAML.

---

## Step 3: Name

Prompt the user to enter a name, or type `random` to have the LLM generate one.

### Random name via LLM

- Call the configured LLM (same provider/config as the narrator in `systems/narrator.py`).
- Prompt: ask for a single, appropriate fantasy name for a `<gender>` `<ancestry>` character in the Shadowdark setting — no explanation, just the name.
- Display the generated name and ask the user to confirm or re-roll (`y` to accept, `n` to generate another, or type a custom name to override).

---

## Step 4: Class

After the initial YAML is written, prompt the user to choose a class:

| Choice    | Result                                               |
|-----------|------------------------------------------------------|
| `Fighter` | class set to `Fighter`                               |
| `Priest`  | class set to `Priest`                                |
| `Thief`   | class set to `Thief`                                 |
| `Wizard`  | class set to `Wizard`                                |
| `Random`  | system randomly selects one of the four classes above |

Use `prompt_toolkit` with autocomplete on the five options (case-insensitive). Re-prompt on invalid input. Display the resolved class, then roll HP (see HP Rolling below), update `meta.class` and `combat.hp` in the existing YAML file, and load the character.

---

## Output: YAML File

Write a new file to `data/shadowdark/<slugified_name>.yaml`. The initial schema mirrors the Shadowdark character schema (see CLAUDE.md) with placeholder/default values:

```yaml
meta:
  name: <name>
  system: shadowdark
  ancestry: <ancestry>
  class: ""  # filled in Step 4
  gender: <chosen or random>
  pronouns: <auto or prompted>
  level: 1
  status: ongoing

combat:
  hp: 0  # filled in Step 3 after class is chosen
  ac_normal: <10 + DEX mod>
  ac_shield: <ac_normal + 2>

stats:
  str: <rolled>
  dex: <rolled>
  con: <rolled>
  int: <rolled>
  wis: <rolled>
  cha: <rolled>

gold: <rolled>

languages:
  - Common
  # ancestry bonus languages appended here

weapons: []

spells: {}

talents: []

backstory: <rolled background title>  # e.g. "Sailor"
backstory_detail: <background description>  # e.g. "Pirate, privateer, or merchant — the seas are yours"
personality_and_hooks: ""
campaign_context: ""
```

### HP Rolling

HP is rolled after class and stats are known. The hit die depends on class:

| Class   | Hit Die |
|---------|---------|
| Fighter | 1d8     |
| Priest  | 1d6     |
| Thief   | 1d4     |
| Wizard  | 1d4     |

Add the CON modifier (`(con - 10) // 2`) to the roll.

**Dwarf bonus:** if the character's ancestry is Dwarf, roll the hit die with advantage (roll twice, take the higher) and add an additional +2 to the result.

Display the roll(s) and final HP to the user. Store the result in `combat.hp`.

### Stat Rolling

Roll 3d6 for each stat in order: STR, DEX, CON, INT, WIS, CHA. If no single stat is 14 or higher, discard all six rolls and repeat until at least one stat meets the threshold. Display each roll to the user as it is resolved.

### AC

`ac_normal = 10 + DEX modifier` (standard formula: `(dex - 10) // 2`). `ac_shield = ac_normal + 2`.

### Starting Gold

Roll 2d6 and multiply by 5. Store as `gold` on the character.

### Languages

All characters start with `Common`. Additional languages by ancestry:

| Ancestry   | Bonus languages       |
|------------|-----------------------|
| Elf        | Elvish, Sylvan        |
| Dwarf      | Dwarvish              |
| Half-Orc   | Orcish                |
| Goblin     | Goblin                |
| Human      | *(player's choice — see below)* |
| Halfling   | *(none)*              |

### Backstory

Roll 1d20 and assign the result from this table (1-indexed):

| d20 | Background              | Detail                                                  |
|-----|-------------------------|---------------------------------------------------------|
| 1   | Urchin                  | You grew up in the merciless streets of a large city    |
| 2   | Wanted                  | There's a price on your head, but you have allies       |
| 3   | Cult Initiate           | You know blasphemous secrets and rituals                |
| 4   | Thieve's Guild          | You have connections, contacts, and debts               |
| 5   | Banished                | Your people cast you out for supposed crimes            |
| 6   | Orphaned                | An unusual guardian rescued and raised you              |
| 7   | Wizard's Apprentice     | You have a knack and eye for magic                      |
| 8   | Jeweler                 | You can easily appraise value and authenticity          |
| 9   | Herbalist               | You know plants, medicines, and poisons                 |
| 10  | Barbarian               | You left the horde, but it never quite left you         |
| 11  | Mercenary               | You fought friend and foe alike for your coin           |
| 12  | Sailor                  | Pirate, privateer, or merchant — the seas are yours     |
| 13  | Acolyte                 | You're well trained in religious rites and doctrines    |
| 14  | Soldier                 | You served as a fighter in an organized army            |
| 15  | Ranger                  | The woods and wilds are your true home                  |
| 16  | Scout                   | You survived on stealth, observation, and speed         |
| 17  | Minstrel                | You've traveled far with your charm and talent          |
| 18  | Scholar                 | You know much about ancient history and lore            |
| 19  | Noble                   | A famous name has opened many doors for you             |
| 20  | Chirurgeon              | You know anatomy, surgery, and first aid                |

Display the roll and result to the user. Store the background title in `backstory` and the detail in `backstory_detail`.

### Languages (continued)

Humans choose one additional language. The full language list is not yet defined; during character creation print a notice: `"Humans may add one additional language. Edit your character YAML to add it to the languages list when you have the options."` Do not prompt for input — just inform and continue.

Filename slug: lowercase, spaces replaced with hyphens, non-alphanumeric characters removed (e.g. `Gruk Half-Orc` → `gruk-half-orc.yaml`).

If a file with that name already exists, append `_2`, `_3`, etc. until the name is unique.

---

## Error Handling

| Situation                        | Behaviour                                                      |
|----------------------------------|----------------------------------------------------------------|
| LLM unavailable for random name  | Print error, fall back to prompting the user to enter a name manually |
| Empty name entered               | Re-prompt                                                      |
| File write fails                 | Print error and return to character menu without loading       |

---

## Files to Change

| File                        | Change                                                                                       |
|-----------------------------|----------------------------------------------------------------------------------------------|
| `systems/shadowdark.py`     | Add `create_character()` flow, LLM name generation helper                                   |
| `roll.py`                   | Add "Create new character" option to the Shadowdark character menu, call `create_character()` |

No new dependencies required; reuse existing `llm_config.yaml` and the `anthropic`/`openai` SDKs already present.
