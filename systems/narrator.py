from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from systems.character import Character

CONFIG_PATH = Path(__file__).parent.parent / "llm_config.yaml"

SYSTEM_PROMPT = """\
You are a masterful fantasy narrator with a gift for cinematic prose. \
You will be given a character sheet and campaign notes for a tabletop RPG character. \
Your task is to bring this character's story to life.

Structure your narration as follows:
1. An evocative introduction to the character — who they are, their personality, \
their history, and what drives them. Draw on all provided backstory and metadata.
2. A session-by-session retelling of the campaign notes, narrated in vivid, \
cinematic prose. Treat each session like a chapter. Honour the tone of the source \
material — do not sanitise drama, failure, or darkness. Name NPCs, describe environments, \
give weight to decisions. Where the notes are sparse, extrapolate with atmospheric detail \
that stays true to the character's voice.

Write for an audience who has just finished playing these sessions and wants to feel \
the story's weight one more time.\
"""


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def _build_user_prompt(character: Character) -> str:
    char_yaml = yaml.dump(character.data, default_flow_style=False, allow_unicode=True)
    return f"Character sheet and campaign notes:\n\n```yaml\n{char_yaml}```"


def _stream_anthropic(config: dict[str, Any], user_prompt: str) -> None:
    try:
        import anthropic
    except ImportError:
        print("The 'anthropic' package is required. Run: .venv/bin/pip install anthropic")
        return

    api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    with client.messages.stream(
        model=config["model"],
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print()


def _stream_openai_compatible(config: dict[str, Any], user_prompt: str) -> None:
    try:
        from openai import OpenAI
    except ImportError:
        print("The 'openai' package is required. Run: .venv/bin/pip install openai")
        return

    api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
    api_key = config.get("api_key") or os.environ.get(api_key_env) or "local"
    base_url = config.get("base_url")

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    stream = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
        max_tokens=4096,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()


def narrate(character: Character) -> None:
    config = _load_config()
    provider = config.get("provider", "anthropic")

    print(f"\n--- Summoning the narrator ({config.get('model', '?')}) ---\n")

    user_prompt = _build_user_prompt(character)

    if provider == "anthropic":
        _stream_anthropic(config, user_prompt)
    elif provider == "openai_compatible":
        _stream_openai_compatible(config, user_prompt)
    else:
        print(f"Unknown provider '{provider}'. Check llm_config.yaml.")
