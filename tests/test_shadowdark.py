from unittest.mock import patch
from systems.shadowdark import parse_notation, roll, ShadowdarkRollResult, check, CheckResult


def _make_character(stats: dict) -> object:
    """Minimal character-like object for check() tests."""
    class FakeChar:
        data = {"stats": stats}
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
        char = _make_character(stats)
        for abbr in ("str", "dex", "con", "int", "wis", "cha"):
            assert check(abbr, char) is not None, f"{abbr} should resolve"
