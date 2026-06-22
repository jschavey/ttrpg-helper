import pytest
from unittest.mock import patch
from systems.shadowdark import parse_notation, roll, ShadowdarkRollResult


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
