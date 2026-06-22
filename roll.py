#!/usr/bin/env python3
from systems.star_wars import StarWarsSystem
from systems.shadowdark import ShadowdarkSystem

SYSTEMS = [
    StarWarsSystem(),
    ShadowdarkSystem(),
]


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
                SYSTEMS[idx].run()
                continue
        print(f"Invalid choice. Enter 1-{len(SYSTEMS)} or q.")


if __name__ == "__main__":
    main_menu()
