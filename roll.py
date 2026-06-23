#!/usr/bin/env python3
from systems.character import Character, load_characters
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


def story_menu() -> None:
    """Present character selection for story narration, grouped by status and system."""
    from systems.narrator import narrate

    # Gather all characters across all systems
    finished: list[tuple[str, Character]] = []
    ongoing: list[tuple[str, Character]] = []

    for system in SYSTEMS:
        for char in load_characters(system.system_slug):
            status = char.data.get("meta", {}).get("status", "ongoing")
            entry = (system.name, char)
            if status == "finished":
                finished.append(entry)
            else:
                ongoing.append(entry)

    if not finished and not ongoing:
        print("\nNo characters found.")
        return

    options: list[tuple[str, Character]] = []

    print()
    idx = 1

    if finished:
        print("-- Finished Campaigns --")
        for system_name, char in finished:
            print(f"{idx}. [{system_name}] {char.name}")
            options.append((system_name, char))
            idx += 1

    if ongoing:
        if finished:
            print()
        print("-- Ongoing Campaigns --")
        for system_name, char in ongoing:
            print(f"{idx}. [{system_name}] {char.name}")
            options.append((system_name, char))
            idx += 1

    print("q. Back")

    while True:
        try:
            choice = input("\nChoose a character: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice in ("q", "quit", "back"):
            return

        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(options):
                _, char = options[i - 1]
                try:
                    narrate(char)
                except KeyboardInterrupt:
                    print("\n(narration interrupted)")
                input("\nPress Enter to continue...")
                return

        print("Invalid choice.")


def main_menu() -> None:
    while True:
        print("\n=== Dice Roller ===")
        for i, system in enumerate(SYSTEMS, 1):
            print(f"{i}. {system.name}")
        story_idx = len(SYSTEMS) + 1
        print(f"{story_idx}. Relive an epic story")
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
            if idx == story_idx - 1:
                story_menu()
                continue
        print(f"Invalid choice. Enter 1-{story_idx} or q.")


if __name__ == "__main__":
    main_menu()
