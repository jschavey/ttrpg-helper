from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import yaml

from systems.character import Character

CONFIG_PATH = Path(__file__).parent.parent / "llm_config.yaml"

SYSTEM_PROMPT = """\
You are a masterful narrator with a gift for cinematic prose, equally at home in \
grim fantasy dungeons and the far reaches of a galaxy far, far away. \
You will be given a character sheet and campaign notes for a tabletop RPG character. \
Your task is to bring this character's story to life.

SETTING AWARENESS — if the character sheet includes a `campaign_context` field, \
treat it as canonical truth about the world, the political situation, and the \
mission stakes. Ground the narration in that setting. For Star Wars D6 characters \
this means honouring the lived texture of the WEG Star Wars universe: the smell of \
blaster ozone in a cantina, the weight of the Empire's boot on occupied worlds, the \
eerie hum of a lightsaber in the dark, the crackle of a comm unit cutting out at the \
worst moment. The Force is real, the stakes are galactic, and every street-level \
decision echoes against that backdrop.

CRITICAL — translate every stat into behavioural truth. Never reference dice codes, \
numerical attribute scores, or stat values directly in the prose. The numbers are \
your source material, not your vocabulary. A character with low physical coordination \
moves with deliberate, calculated weight rather than grace — their body a liability \
they have learned to work around. A character with exceptional perception catches the \
tells others miss — the micro-expression, the weight shift, the hand that moves too \
slowly toward a holster. A character with low physical strength avoids confrontation \
for very good reason and knows it. Do not let a character's self-image or personality \
override what their abilities say is actually true about them — the tension between \
self-perception and reality is where the best character moments live. Use the full \
stat block; do not ignore middling or weak attributes.

Structure your narration as follows:
1. An evocative introduction to the character — who they are, their personality, \
their history, and what drives them. Ground their traits in their actual capabilities: \
show which behaviours, habits, and limitations emerge from who they truly are. Be \
honest about their weaknesses as much as their strengths. If a campaign_context is \
present, open by painting the wider setting so the reader feels the world before \
meeting the character.
2. A session-by-session retelling of the campaign notes, narrated in vivid, \
cinematic prose. Treat each session like a chapter. At every meaningful moment, \
let the relevant ability colour the narration through action and consequence, never \
through numerical annotation. Honour the tone of the source material — do not \
sanitise drama, failure, or darkness. Name NPCs, describe environments, give weight \
to decisions. Where the notes are sparse, extrapolate with atmospheric detail that \
stays true to both the character's voice and their actual capabilities.

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


def _print_connection_error(endpoint: str | None, exc: Exception) -> None:
    label = endpoint or "the API endpoint"
    print(f"\n[Narrator unavailable] Could not reach {label}.")
    detail = str(exc)
    if detail:
        print(f"  {detail}")
    print("Check that your LLM server is running and a model is loaded, then try again.")


def _stream_anthropic(config: dict[str, Any], user_prompt: str) -> None:
    try:
        import anthropic
    except ImportError:
        print("The 'anthropic' package is required. Run: .venv/bin/pip install anthropic")
        return

    api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    try:
        t0 = time.monotonic()
        with client.messages.stream(
            model=config["model"],
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            final = stream.get_final_message()
        elapsed = time.monotonic() - t0
        out_tokens = final.usage.output_tokens
        print(f"\n\n--- {elapsed:.1f}s | {out_tokens} tokens | {out_tokens / elapsed:.1f} tok/s ---")
    except Exception as e:
        _print_connection_error("Anthropic API", e)


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

    try:
        t0 = time.monotonic()
        token_count = 0
        stream = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            stream_options={"include_usage": True},
            max_tokens=16384,
        )
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
            if chunk.usage:
                token_count = chunk.usage.completion_tokens
        elapsed = time.monotonic() - t0
        tps = token_count / elapsed if elapsed > 0 else 0
        print(f"\n\n--- {elapsed:.1f}s | {token_count} tokens | {tps:.1f} tok/s ---")
    except Exception as e:
        _print_connection_error(base_url, e)


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
