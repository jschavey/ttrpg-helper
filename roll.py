#!/usr/bin/env python3
import random
import re


def roll_d6():
    return random.randint(1, 6)


def parse_notation(notation):
    notation = notation.strip().upper()
    match = re.fullmatch(r'(\d+)D(?:\+(\d+))?', notation)
    if not match:
        print(f"Invalid notation: '{notation}'. Use format like '6D' or '4D+2'.")
        return None
    num_dice = int(match.group(1))
    bonus = int(match.group(2)) if match.group(2) else 0
    return num_dice, bonus


def roll_pool(notation):
    result = parse_notation(notation)
    if result is None:
        return
    num_dice, bonus = result

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


def run_star_wars():
    print_difficulty_table()
    print("\nEnter dice notation (e.g. 6D, 4D+2) or 'q' to quit.")
    while True:
        try:
            notation = input("\nRoll> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if notation.lower() in ("q", "quit", "exit"):
            break
        if notation:
            roll_pool(notation)


def parse_shadowdark_notation(notation):
    """Parse notation like 2D6+1, D20, 3D8-2. Returns ([(count, sides), ...], modifier)."""
    notation = notation.strip().upper()
    # Strip optional leading spaces around + or -
    match = re.fullmatch(r'((?:\d*D\d+)(?:[+\-]\d*D\d+)*)(([+\-]\d+))?', notation)
    if not match:
        print(f"Invalid notation: '{notation}'. Use format like '2D6', 'D20+3', '2D6+1D4-2'.")
        return None

    pools_str = match.group(1)
    modifier_str = match.group(3)  # e.g. "+1" or "-3"

    pool_pattern = re.findall(r'([+\-]?)(\d*)D(\d+)', pools_str)
    pools = []
    for sign, count_str, sides_str in pool_pattern:
        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        if sign == '-':
            count = -count
        pools.append((count, sides))

    modifier = int(modifier_str) if modifier_str else 0
    return pools, modifier


def _roll_once(pools, modifier, label):
    print(f"  [{label}]")
    all_rolls = []
    for count, sides in pools:
        sign = -1 if count < 0 else 1
        for _ in range(abs(count)):
            roll = random.randint(1, sides)
            all_rolls.append(sign * roll)
            die_label = f"d{sides}" if sign == 1 else f"-d{sides}"
            print(f"    {die_label}: {roll}")
    dice_total = sum(all_rolls)
    total = dice_total + modifier
    if modifier:
        print(f"    Dice: {dice_total}  {modifier:+d}")
    print(f"    Subtotal: {total}")
    return total


def roll_shadowdark(notation, advantage=None):
    result = parse_shadowdark_notation(notation)
    if result is None:
        return
    pools, modifier = result

    adv_label = " (advantage)" if advantage is True else " (disadvantage)" if advantage is False else ""
    print(f"\nRolling {notation}{adv_label}:")

    if advantage is None:
        all_rolls = []
        for count, sides in pools:
            sign = -1 if count < 0 else 1
            for _ in range(abs(count)):
                roll = random.randint(1, sides)
                all_rolls.append(sign * roll)
                label = f"d{sides}" if sign == 1 else f"-d{sides}"
                print(f"  {label}: {roll}")
        dice_total = sum(all_rolls)
        total = dice_total + modifier
        if modifier:
            print(f"\n  Dice: {dice_total}  {modifier:+d}")
        print(f"  Total: {total}")
    else:
        total_a = _roll_once(pools, modifier, "Roll 1")
        total_b = _roll_once(pools, modifier, "Roll 2")
        if advantage:
            chosen = max(total_a, total_b)
            rule = "higher"
        else:
            chosen = min(total_a, total_b)
            rule = "lower"
        print(f"\n  Taking {rule}: {chosen}")


def run_shadowdark():
    print("\nEnter dice notation (e.g. D20, 2D6+1, D20-3) or 'q' to quit.")
    print("Append 'a' for advantage or 'd' for disadvantage (e.g. 2D6+1 a, D20 d).")
    while True:
        try:
            raw = input("\nRoll> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if raw.lower() in ("q", "quit", "exit"):
            break
        if not raw:
            continue
        parts = raw.split()
        suffix = parts[-1].lower() if len(parts) > 1 else ""
        if suffix == "a":
            notation = " ".join(parts[:-1])
            advantage = True
        elif suffix == "d":
            notation = " ".join(parts[:-1])
            advantage = False
        else:
            notation = raw
            advantage = None
        roll_shadowdark(notation, advantage)


def main_menu():
    while True:
        print("\n=== Dice Roller ===")
        print("1. Star Wars D6")
        print("2. Shadowdark")
        print("q. Quit")
        try:
            choice = input("\nChoose a system: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if choice == "1":
            run_star_wars()
        elif choice == "2":
            run_shadowdark()
        elif choice in ("q", "quit", "exit"):
            break
        else:
            print("Invalid choice. Enter 1, 2, or q.")


if __name__ == "__main__":
    main_menu()
