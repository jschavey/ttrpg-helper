import pytest
from unittest.mock import patch
from systems.star_wars_d6 import parse_notation, roll, RollResult as StarWarsRollResult


class TestParseNotation:
    def test_basic_dice(self):
        assert parse_notation("6D") == (6, 0)

    def test_dice_with_bonus(self):
        assert parse_notation("4D+2") == (4, 2)

    def test_lowercase(self):
        assert parse_notation("3d") == (3, 0)

    def test_whitespace_stripped(self):
        assert parse_notation("  5D+1  ") == (5, 1)

    def test_invalid_no_d(self):
        assert parse_notation("6") is None

    def test_invalid_empty(self):
        assert parse_notation("") is None

    def test_invalid_shadowdark_style(self):
        assert parse_notation("D20") is None

    def test_one_die(self):
        assert parse_notation("1D") == (1, 0)


class TestRoll:
    def test_returns_result_object(self):
        result = roll("3D")
        assert isinstance(result, StarWarsRollResult)

    def test_invalid_notation_returns_none(self):
        assert roll("bad") is None

    def test_total_includes_bonus(self):
        with patch("systems.star_wars_d6.random.randint", return_value=3):
            result = roll("2D+5")
        # rolls: [3, 3], bonus: 5
        assert result.total == 11

    def test_no_complication_no_explode_on_normal_roll(self):
        with patch("systems.star_wars_d6.random.randint", return_value=3):
            result = roll("3D")
        assert not result.complication
        assert not result.exploded

    def test_complication_on_wild_die_1(self):
        # First call returns 1 (wild die), rest return 3
        with patch("systems.star_wars_d6.random.randint", side_effect=[1, 3, 3]):
            result = roll("3D")
        assert result.complication
        assert not result.exploded

    def test_explode_on_wild_die_6(self):
        # First call returns 6 (wild die explodes), bonus roll returns 4, rest return 2
        with patch("systems.star_wars_d6.random.randint", side_effect=[6, 4, 2, 2]):
            result = roll("3D")
        assert result.exploded
        assert not result.complication
        # rolls: [6, 4, 2, 2], bonus: 0
        assert result.total == 14

    def test_flags_empty_on_normal(self):
        with patch("systems.star_wars_d6.random.randint", return_value=4):
            result = roll("2D")
        assert result.flags == []

    def test_flags_both(self):
        # wild die = 1 gives complication; 1 != 6 so no explode
        with patch("systems.star_wars_d6.random.randint", side_effect=[1, 3]):
            result = roll("2D")
        assert "COMPLICATION" in result.flags
        assert "EXPLODE" not in result.flags
