#!/usr/bin/env python3
import random
import sys
import re


def roll_d6():
    return random.randint(1, 6)


def parse_notation(notation):
    notation = notation.strip().upper()
    match = re.fullmatch(r'(\d+)D(?:\+(\d+))?', notation)
    if not match:
        print(f"Invalid notation: '{notation}'. Use format like '6D' or '4D+2'.")
        sys.exit(1)
    num_dice = int(match.group(1))
    bonus = int(match.group(2)) if match.group(2) else 0
    return num_dice, bonus


def roll_pool(notation):
    num_dice, bonus = parse_notation(notation)

    print(f"\nRolling {notation}:")
    print(f"  {'Special die' if num_dice >= 1 else ''}")

    rolls = []
    special_first = None
    special_second = None
    exploded = False

    for i in range(num_dice):
        result = roll_d6()
        if i == 0:
            special_first = result
            if result == 6:
                special_second = roll_d6()
                exploded = True
                print(f"  Die 1 (special): {result} -> EXPLODES! Bonus roll: {special_second}")
            else:
                print(f"  Die 1 (special): {result}")
            rolls.append(result)
            if special_second is not None:
                rolls.append(special_second)
        else:
            print(f"  Die {i + 1}: {result}")
            rolls.append(result)

    total = sum(rolls) + bonus

    flags = []
    if exploded:
        flags.append("EXPLODE")
    if special_first == 1:
        flags.append("COMPLICATION")

    flag_str = "  [" + " | ".join(flags) + "]" if flags else ""

    if bonus:
        print(f"\n  Dice sum: {sum(rolls)}  +  bonus: {bonus}")
    print(f"  Total: {total}{flag_str}")


DIFFICULTY_TABLE = [
    ("Very Easy",      "1-5"),
    ("Easy",           "6-10"),
    ("Moderate",       "11-15"),
    ("Difficult",      "16-20"),
    ("Very Difficult", "21-30"),
    ("Heroic",         "31+"),
]


def print_difficulty_table():
    print("\n  Difficulty Reference:")
    print("  +-----------------+-------+")
    print("  | Difficulty      | Score |")
    print("  +-----------------+-------+")
    for label, score in DIFFICULTY_TABLE:
        print(f"  | {label:<15}  | {score:<5} |")
    print("  +-----------------+-------+")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python roll.py <notation> [notation ...]")
        print("Examples: python roll.py 6D    python roll.py 4D+2")
        sys.exit(1)

    print_difficulty_table()

    for arg in sys.argv[1:]:
        roll_pool(arg)
