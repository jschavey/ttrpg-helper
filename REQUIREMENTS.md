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
