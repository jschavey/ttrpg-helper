from unittest.mock import patch
from systems.shadowdark import (
    parse_notation, roll, ShadowdarkRollResult,
    check, CheckResult,
    cast, CastResult, get_character_spells, _parse_cast_args,
    _CommandCompleter,
)


def _make_character(
    stats: dict | None = None,
    meta: dict | None = None,
    talents: list | None = None,
    spells: dict | None = None,
) -> object:
    class FakeChar:
        data = {
            "stats": stats or {},
            "meta": meta or {},
            "talents": talents or [],
            "spells": spells or {},
        }
    return FakeChar()


class TestParseNotation:
    def test_d20(self):
        assert parse_notation("D20") == ([(1, 20)], 0)

    def test_2d6(self):
        assert parse_notation("2D6") == ([(2, 6)], 0)

    def test_with_positive_modifier(self):
        assert parse_notation("D20+3") == ([(1, 20)], 3)

    def test_with_negative_modifier(self):
        assert parse_notation("D20-3") == ([(1, 20)], -3)

    def test_mixed_pool(self):
        result = parse_notation("2D6+1D4")
        assert result is not None
        pools, mod = result
        assert pools == [(2, 6), (1, 4)]
        assert mod == 0

    def test_mixed_pool_with_modifier(self):
        result = parse_notation("2D6+1D4-2")
        assert result is not None
        pools, mod = result
        assert pools == [(2, 6), (1, 4)]
        assert mod == -2

    def test_negative_die_count(self):
        result = parse_notation("2D6-1D4")
        assert result is not None
        pools, _ = result
        assert pools == [(2, 6), (-1, 4)]

    def test_invalid_returns_none(self):
        assert parse_notation("bad") is None

    def test_empty_returns_none(self):
        assert parse_notation("") is None


class TestRoll:
    def test_returns_result_object(self):
        result = roll("D20")
        assert isinstance(result, ShadowdarkRollResult)

    def test_invalid_returns_none(self):
        assert roll("xyz") is None

    def test_total_with_modifier(self):
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = roll("D20+3")
        assert result is not None
        assert result.total == 13

    def test_total_negative_modifier(self):
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = roll("D20-3")
        assert result is not None
        assert result.total == 7

    def test_no_advantage(self):
        result = roll("D20")
        assert result is not None
        assert result.advantage is None
        assert result.alt_rolls is None

    def test_advantage_picks_higher(self):
        with patch("systems.shadowdark.random.randint", side_effect=[5, 15]):
            result = roll("D20", advantage=True)
        assert result is not None
        assert result.chosen_total == 15

    def test_disadvantage_picks_lower(self):
        with patch("systems.shadowdark.random.randint", side_effect=[5, 15]):
            result = roll("D20", advantage=False)
        assert result is not None
        assert result.chosen_total == 5

    def test_mixed_pool_total(self):
        # 2D6 → [3, 3], 1D4 → [2]; total = 8
        with patch("systems.shadowdark.random.randint", side_effect=[3, 3, 2]):
            result = roll("2D6+1D4")
        assert result is not None
        assert result.total == 8

    def test_negative_die_subtracts(self):
        # 2D6 → [4, 4], -1D4 → -[2]; total = 4+4-2 = 6
        with patch("systems.shadowdark.random.randint", side_effect=[4, 4, 2]):
            result = roll("2D6-1D4")
        assert result is not None
        assert result.total == 6


class TestCheck:
    def test_unknown_check_returns_none(self):
        char = _make_character({"wis": 14})
        assert check("alchemy", char) is None

    def test_missing_stat_returns_none(self):
        # character sheet has no wis entry
        char = _make_character({})
        assert check("wis", char) is None

    def test_returns_check_result(self):
        char = _make_character({"wis": 14})
        result = check("wis", char)
        assert isinstance(result, CheckResult)

    def test_stat_name_resolves(self):
        char = _make_character({"wis": 14})
        result = check("wisdom", char)
        assert result is not None
        assert result.stat_key == "wis"

    def test_named_check_resolves_to_stat(self):
        char = _make_character({"wis": 14})
        result = check("perception", char)
        assert result is not None
        assert result.stat_key == "wis"
        assert result.check_name == "Perception"

    def test_abbreviation_resolves(self):
        char = _make_character({"wis": 14})
        result = check("perc", char)
        assert result is not None
        assert result.stat_key == "wis"

    def test_total_equals_roll_plus_mod(self):
        char = _make_character({"str": 16})  # mod = +3
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = check("str", char)
        assert result is not None
        assert result.total == 13

    def test_negative_modifier(self):
        char = _make_character({"str": 8})  # mod = -1
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = check("str", char)
        assert result is not None
        assert result.total == 9

    def test_no_advantage_by_default(self):
        char = _make_character({"dex": 12})
        result = check("dex", char)
        assert result is not None
        assert result.advantage is None
        assert result.alt_die_roll is None

    def test_advantage_picks_higher(self):
        char = _make_character({"dex": 10})  # mod = 0
        with patch("systems.shadowdark.random.randint", side_effect=[4, 18]):
            result = check("dex", char, advantage=True)
        assert result is not None
        assert result.chosen_total == 18

    def test_disadvantage_picks_lower(self):
        char = _make_character({"dex": 10})  # mod = 0
        with patch("systems.shadowdark.random.randint", side_effect=[4, 18]):
            result = check("dex", char, advantage=False)
        assert result is not None
        assert result.chosen_total == 4

    def test_advantage_modifier_applied_to_chosen(self):
        char = _make_character({"wis": 16})  # mod = +3
        with patch("systems.shadowdark.random.randint", side_effect=[5, 12]):
            result = check("wis", char, advantage=True)
        assert result is not None
        assert result.chosen_total == 15  # 12 + 3

    def test_all_stat_abbreviations_resolve(self):
        stats = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}
        char = _make_character(stats=stats)
        for abbr in ("str", "dex", "con", "int", "wis", "cha"):
            assert check(abbr, char) is not None, f"{abbr} should resolve"


class TestParseCastArgs:
    def test_spell_name_only(self):
        assert _parse_cast_args(["Cure", "Wounds"]) == ("Cure Wounds", 0, None)

    def test_advantage_suffix(self):
        assert _parse_cast_args(["Cure", "Wounds", "a"]) == ("Cure Wounds", 0, True)

    def test_disadvantage_suffix(self):
        assert _parse_cast_args(["Cure", "Wounds", "d"]) == ("Cure Wounds", 0, False)

    def test_positive_situational(self):
        assert _parse_cast_args(["Cure", "Wounds", "+2"]) == ("Cure Wounds", 2, None)

    def test_negative_situational(self):
        assert _parse_cast_args(["Cure", "Wounds", "-1"]) == ("Cure Wounds", -1, None)

    def test_situational_and_advantage(self):
        assert _parse_cast_args(["Cure", "Wounds", "+1", "a"]) == ("Cure Wounds", 1, True)

    def test_situational_and_disadvantage(self):
        assert _parse_cast_args(["Cure", "Wounds", "-2", "d"]) == ("Cure Wounds", -2, False)

    def test_empty_parts(self):
        spell, sit, adv = _parse_cast_args([])
        assert spell == "" and sit == 0 and adv is None


class TestCast:
    def test_returns_cast_result(self):
        char = _make_character(stats={"wis": 14}, meta={"class": "Priest"})
        result = cast("Cure Wounds", char)
        assert isinstance(result, CastResult)

    def test_priest_uses_wis_mod(self):
        char = _make_character(stats={"wis": 15}, meta={"class": "Priest"})
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Cure Wounds", char)
        # WIS 15 → mod +2; total = 10 + 2 = 12
        assert result.total == 12

    def test_wizard_uses_int_mod(self):
        char = _make_character(stats={"int": 16}, meta={"class": "Wizard"})
        with patch("systems.shadowdark.random.randint", return_value=8):
            result = cast("Magic Missile", char)
        # INT 16 → mod +3; total = 8 + 3 = 11
        assert result.total == 11

    def test_unknown_class_no_stat_mod(self):
        char = _make_character(stats={"wis": 18}, meta={"class": "Fighter"})
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Something", char)
        assert result.total == 10
        assert result.modifiers == []

    def test_priest_talent_bonus_single(self):
        char = _make_character(
            stats={"wis": 10},
            meta={"class": "Priest"},
            talents=["+1 to priest spellcasting checks"],
        )
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Cure Wounds", char)
        # WIS 10 → mod 0; talent +1; total = 11
        assert result.total == 11

    def test_priest_talent_bonus_stacks(self):
        char = _make_character(
            stats={"wis": 10},
            meta={"class": "Priest"},
            talents=["+1 to priest spellcasting checks", "+1 to priest spellcasting checks"],
        )
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Cure Wounds", char)
        # talent +2; total = 12
        assert result.total == 12

    def test_wizard_ignores_priest_talents(self):
        char = _make_character(
            stats={"int": 10},
            meta={"class": "Wizard"},
            talents=["+1 to priest spellcasting checks"],
        )
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Magic Missile", char)
        assert result.total == 10

    def test_situational_modifier_positive(self):
        char = _make_character(stats={"wis": 10}, meta={"class": "Priest"})
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Cure Wounds", char, situational=2)
        assert result.total == 12

    def test_situational_modifier_negative(self):
        char = _make_character(stats={"wis": 10}, meta={"class": "Priest"})
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Cure Wounds", char, situational=-3)
        assert result.total == 7

    def test_no_advantage_by_default(self):
        char = _make_character(stats={"wis": 10}, meta={"class": "Priest"})
        result = cast("Cure Wounds", char)
        assert result.advantage is None
        assert result.alt_die_roll is None

    def test_advantage_picks_higher(self):
        char = _make_character(stats={"wis": 10}, meta={"class": "Priest"})
        with patch("systems.shadowdark.random.randint", side_effect=[5, 17]):
            result = cast("Cure Wounds", char, advantage=True)
        assert result.chosen_total == 17

    def test_disadvantage_picks_lower(self):
        char = _make_character(stats={"wis": 10}, meta={"class": "Priest"})
        with patch("systems.shadowdark.random.randint", side_effect=[5, 17]):
            result = cast("Cure Wounds", char, advantage=False)
        assert result.chosen_total == 5

    def test_all_modifiers_in_audit_trail(self):
        char = _make_character(
            stats={"wis": 15},
            meta={"class": "Priest"},
            talents=["+1 to priest spellcasting checks"],
        )
        result = cast("Cure Wounds", char, situational=1)
        labels = [label for label, _ in result.modifiers]
        assert any("WIS" in l for l in labels)
        assert any("Talent" in l for l in labels)
        assert any("Situational" in l for l in labels)

    def test_modifier_values_sum_to_total_minus_roll(self):
        char = _make_character(
            stats={"wis": 15},
            meta={"class": "Priest"},
            talents=["+1 to priest spellcasting checks"],
        )
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = cast("Cure Wounds", char, situational=2)
        mod_sum = sum(v for _, v in result.modifiers)
        assert result.total == result.die_roll + mod_sum


class TestInitiative:
    """Initiative is a DEX check with the label overridden to 'Initiative'."""

    def test_uses_dex_stat(self):
        char = _make_character({"dex": 14})
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = check("dex", char)
        assert result is not None
        result.check_name = "Initiative"
        assert result.stat_key == "dex"

    def test_total_dex_mod_applied(self):
        char = _make_character({"dex": 14})  # mod = +2
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = check("dex", char)
        assert result is not None
        assert result.total == 12

    def test_negative_dex_mod(self):
        char = _make_character({"dex": 8})  # mod = -1
        with patch("systems.shadowdark.random.randint", return_value=10):
            result = check("dex", char)
        assert result is not None
        assert result.total == 9

    def test_advantage_picks_higher(self):
        char = _make_character({"dex": 10})  # mod = 0
        with patch("systems.shadowdark.random.randint", side_effect=[3, 17]):
            result = check("dex", char, advantage=True)
        assert result is not None
        assert result.chosen_total == 17

    def test_disadvantage_picks_lower(self):
        char = _make_character({"dex": 10})  # mod = 0
        with patch("systems.shadowdark.random.randint", side_effect=[3, 17]):
            result = check("dex", char, advantage=False)
        assert result is not None
        assert result.chosen_total == 3

    def test_advantage_applies_mod_to_chosen(self):
        char = _make_character({"dex": 16})  # mod = +3
        with patch("systems.shadowdark.random.randint", side_effect=[6, 14]):
            result = check("dex", char, advantage=True)
        assert result is not None
        assert result.chosen_total == 17  # 14 + 3

    def test_missing_dex_returns_none(self):
        char = _make_character({})
        assert check("dex", char) is None

    def test_label_override(self):
        char = _make_character({"dex": 10})
        result = check("dex", char)
        assert result is not None
        result.check_name = "Initiative"
        assert result.check_name == "Initiative"


class TestCommandCompleterRollInit:
    def test_init_in_roll_options(self):
        completer = _CommandCompleter([])
        assert "init" in completer._roll_options

    def test_completes_init_after_roll(self):
        from prompt_toolkit.document import Document
        completer = _CommandCompleter([])
        doc = Document("roll i", len("roll i"))
        completions = list(completer.get_completions(doc, None))
        assert any(c.text == "init" for c in completions)

    def test_no_completion_without_roll_prefix(self):
        from prompt_toolkit.document import Document
        completer = _CommandCompleter([])
        doc = Document("init", len("init"))
        completions = list(completer.get_completions(doc, None))
        assert completions == []

    def test_full_init_still_completes(self):
        from prompt_toolkit.document import Document
        completer = _CommandCompleter([])
        doc = Document("roll init", len("roll init"))
        completions = list(completer.get_completions(doc, None))
        assert any(c.text == "init" for c in completions)

    def test_roll_does_not_complete_spells(self):
        from prompt_toolkit.document import Document
        completer = _CommandCompleter(["Cure Wounds"])
        doc = Document("roll C", len("roll C"))
        completions = list(completer.get_completions(doc, None))
        assert not any(c.text == "Cure Wounds" for c in completions)


class TestGetCharacterSpells:
    def test_extracts_all_tiers(self):
        char = _make_character(spells={
            "tier_1": ["Cure Wounds", "Turn Undead"],
            "tier_2": ["Augury"],
        })
        spells = get_character_spells(char)
        assert set(spells) == {"Cure Wounds", "Turn Undead", "Augury"}

    def test_empty_spells(self):
        char = _make_character()
        assert get_character_spells(char) == []

    def test_single_tier(self):
        char = _make_character(spells={"tier_1": ["Cure Wounds"]})
        assert get_character_spells(char) == ["Cure Wounds"]
