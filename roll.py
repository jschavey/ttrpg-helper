#!/usr/bin/env python3
from systems.character import load_characters
from systems.star_wars import StarWarsSystem
from systems.shadowdark import ShadowdarkSystem

SYSTEMS = [
    StarWarsSystem(),
    ShadowdarkSystem(),
]


def character_menu(system_slug: str):
    """Present character selection for the given system. Returns chosen character or None."""
    characters = load_characters(system_slug)

    print()
    options = list(characters)
    for i, char in enumerate(options, 1):
        print(f"{i}. {char.name}")
    new_idx = len(options) + 1
    none_idx = len(options) + 2
    print(f"{new_idx}. New  (not yet implemented)")
    print(f"{none_idx}. None  (raw dice roller)")
    print("q. Back")

    while True:
        try:
            choice = input("\nChoose a character: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

        if choice in ("q", "quit", "back"):
            return "back"

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
            if idx == new_idx:
                print("New character creation is not yet implemented.")
                continue
            if idx == none_idx:
                return None

        print(f"Invalid choice.")


def main_menu() -> None:
    while True:
        print("\n=== Dice Roller ===")
        for i, system in enumerate(SYSTEMS, 1):
            print(f"{i}. {system.name}")
        print("q. Quit")
        try:
            choice = input("\nChoose a system: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if choice in ("q", "quit", "exit"):
            break
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(SYSTEMS):
                system = SYSTEMS[idx]
                result = character_menu(system.system_slug)
                if result == "back":
                    continue
                system.run(character=result)
                continue
        print(f"Invalid choice. Enter 1-{len(SYSTEMS)} or q.")


if __name__ == "__main__":
    main_menu()
