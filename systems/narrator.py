from __future__ import annotations

import copy
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from systems.character import Character

CONFIG_PATH = Path(__file__).parent.parent / "llm_config.yaml"
NARRATIONS_DIR = Path(__file__).parent.parent / "data" / "narrations"

SESSION_HEADER_RE = re.compile(r"(?m)^[ \t]*(Session\s+\d+[^\n]*)\n")
SESSION_NUMBER_RE = re.compile(r"\d+")

STYLE_GUIDE = """\
You are a masterful narrator with a gift for cinematic prose, equally at home in \
grim fantasy dungeons and the far reaches of a galaxy far, far away.

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
stat block; do not ignore middling or weak attributes.\
"""

SYSTEM_PROMPT_INTRO = f"""\
{STYLE_GUIDE}

You will be given a character sheet for a tabletop RPG character (campaign session \
notes have been withheld for this step — you are writing the introduction only).

Write an evocative introduction to the character — who they are, their personality, \
their history, and what drives them. Ground their traits in their actual capabilities: \
show which behaviours, habits, and limitations emerge from who they truly are. Be \
honest about their weaknesses as much as their strengths. If a campaign_context field \
is present, open by painting the wider setting so the reader feels the world before \
meeting the character.

Write for an audience who has just finished playing this character's campaign and \
wants to feel their story's weight one more time. Do not summarize or foreshadow \
specific session events — you have not been given them. This is character and world \
scene-setting only.\
"""

SYSTEM_PROMPT_SESSION = f"""\
{STYLE_GUIDE}

You will be given a character sheet and the raw campaign notes for ONE session of \
play, plus a short recap of how the previous chapter ended. Narrate this session, \
and only this session, as a single vivid chapter in a cinematic retelling. Treat it \
like a chapter in a novel. At every meaningful moment, let the relevant ability colour \
the narration through action and consequence, never through numerical annotation. \
Honour the tone of the source material — do not sanitise drama, failure, or darkness. \
Name NPCs, describe environments, give weight to decisions. Where the notes are \
sparse, extrapolate with atmospheric detail that stays true to both the character's \
voice and their actual capabilities.

Do not compress or summarize the notes — the raw notes for this session are your \
full source material; render their events in the same level of detail you would give \
any other session, regardless of how much material earlier or later sessions had. \
Do not write an ending or epilogue for the overall story; end at the close of this \
session's events, ready to continue.

If a raw voice transcript is also provided for this session, treat the shorthand \
session notes as ground truth for what happened — they are the player's own curated \
record. The transcript is a rough, error-prone recording (garbled words, mis-heard \
names, crosstalk) and exists only to add texture: specific phrasing, a joke, an aside, \
the way a scene actually played out in the room. Use it to enrich dialogue and \
sensory detail where it plausibly matches or elaborates on a beat already present in \
the shorthand. If the transcript contradicts the shorthand, or describes something \
the shorthand does not corroborate, disregard that detail rather than let a \
transcription error distort the narrative — never let the transcript introduce plot \
points, names, or outcomes the shorthand doesn't support.\
"""


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def _find_session_field(data: dict[str, Any]) -> str | None:
    for key, val in data.items():
        if isinstance(val, str) and SESSION_HEADER_RE.search(val):
            return key
    return None


def _split_sessions(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split a freeform notes field into (preamble, [(header, body), ...])."""
    parts = SESSION_HEADER_RE.split(text)
    preamble = parts[0].strip()
    sessions: list[tuple[str, str]] = []
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sessions.append((header, body))
    return preamble, sessions


def _dump_yaml(data: dict[str, Any]) -> str:
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def _build_intro_prompt(character: Character, session_field: str | None, preamble: str) -> str:
    data = copy.deepcopy(character.data)
    if session_field is not None:
        data[session_field] = preamble
    if "session_transcripts" in data:
        del data["session_transcripts"]
    return f"Character sheet:\n\n```yaml\n{_dump_yaml(data)}```"


def _session_number(header: str) -> str | None:
    match = SESSION_NUMBER_RE.search(header)
    return match.group(0) if match else None


def _get_transcript(character: Character, header: str) -> str | None:
    transcripts = character.data.get("session_transcripts")
    if not isinstance(transcripts, dict):
        return None
    number = _session_number(header)
    for key in (number, header, int(number) if number and number.isdigit() else None):
        if key is not None and key in transcripts:
            text = transcripts[key]
            return text.strip() if isinstance(text, str) and text.strip() else None
    return None


def _build_session_prompt(
    character: Character,
    session_field: str,
    preamble: str,
    header: str,
    body: str,
    previous_tail: str,
    transcript: str | None,
) -> str:
    data = copy.deepcopy(character.data)
    data[session_field] = preamble
    if "session_transcripts" in data:
        del data["session_transcripts"]
    prompt = f"Character sheet:\n\n```yaml\n{_dump_yaml(data)}```\n\n"
    if previous_tail:
        prompt += f"How the previous chapter ended:\n\n{previous_tail}\n\n"
    prompt += f"Raw notes for this session ({header}) — narrate these events now:\n\n{body}"
    if transcript:
        prompt += (
            f"\n\nRaw voice transcript for this session (unreliable — use only to add "
            f"texture where it corroborates the notes above, per your instructions):\n\n"
            f"{transcript}"
        )
    return prompt


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def _save_narration(character: Character, model: str, text: str) -> Path | None:
    if not text.strip():
        return None
    NARRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    filename = f"{_slugify(character.name)}-{stamp}-{_slugify(model)}.md"
    path = NARRATIONS_DIR / filename
    try:
        path.write_text(text)
    except OSError as e:
        print(f"\n[Narrator] Could not save narration: {e}")
        return None
    return path


def _print_connection_error(endpoint: str | None, exc: Exception) -> None:
    label = endpoint or "the API endpoint"
    print(f"\n[Narrator unavailable] Could not reach {label}.")
    detail = str(exc)
    if detail:
        print(f"  {detail}")
    print("Check that your LLM server is running and a model is loaded, then try again.")


def _stream_anthropic(config: dict[str, Any], system_prompt: str, user_prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("The 'anthropic' package is required. Run: .venv/bin/pip install anthropic")
        return ""

    api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    full_text = ""
    try:
        t0 = time.monotonic()
        with client.messages.stream(
            model=config["model"],
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_text += text
            final = stream.get_final_message()
        elapsed = time.monotonic() - t0
        out_tokens = final.usage.output_tokens
        print(f"\n\n--- {elapsed:.1f}s | {out_tokens} tokens | {out_tokens / elapsed:.1f} tok/s ---")
    except Exception as e:
        _print_connection_error("Anthropic API", e)
    return full_text


def _stream_openai_compatible(config: dict[str, Any], system_prompt: str, user_prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        print("The 'openai' package is required. Run: .venv/bin/pip install openai")
        return ""

    api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
    api_key = config.get("api_key") or os.environ.get(api_key_env) or "local"
    base_url = config.get("base_url")

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    full_text = ""
    try:
        t0 = time.monotonic()
        token_count = 0
        stream = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
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
                    full_text += delta
            if chunk.usage:
                token_count = chunk.usage.completion_tokens
        elapsed = time.monotonic() - t0
        tps = token_count / elapsed if elapsed > 0 else 0
        print(f"\n\n--- {elapsed:.1f}s | {token_count} tokens | {tps:.1f} tok/s ---")
    except Exception as e:
        _print_connection_error(base_url, e)
    return full_text


def _stream(config: dict[str, Any], provider: str, system_prompt: str, user_prompt: str) -> str:
    if provider == "anthropic":
        return _stream_anthropic(config, system_prompt, user_prompt)
    elif provider == "openai_compatible":
        return _stream_openai_compatible(config, system_prompt, user_prompt)
    else:
        print(f"Unknown provider '{provider}'. Check llm_config.yaml.")
        return ""


def _last_paragraph(text: str) -> str:
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return paragraphs[-1] if paragraphs else ""


def narrate(character: Character) -> None:
    config = _load_config()
    provider = config.get("provider", "anthropic")
    model = config.get("model", "?")

    session_field = _find_session_field(character.data)
    if session_field is None:
        print(f"\n--- Summoning the narrator ({model}) ---\n")
        char_yaml = _dump_yaml(character.data)
        user_prompt = f"Character sheet and campaign notes:\n\n```yaml\n{char_yaml}```"
        full_text = _stream(
            config,
            provider,
            SYSTEM_PROMPT_INTRO + "\n\n" + SYSTEM_PROMPT_SESSION,
            user_prompt,
        )
        saved_path = _save_narration(character, model, full_text)
        if saved_path:
            print(f"\n[Narrator] Saved to {saved_path.relative_to(saved_path.parent.parent.parent)}")
        return

    preamble, sessions = _split_sessions(character.data[session_field])

    print(f"\n--- Summoning the narrator ({model}) — introduction ---\n")
    intro_prompt = _build_intro_prompt(character, session_field, preamble)
    intro_text = _stream(config, provider, SYSTEM_PROMPT_INTRO, intro_prompt)

    chapters = [intro_text]
    previous_tail = _last_paragraph(intro_text)
    for header, body in sessions:
        print(f"\n\n--- Summoning the narrator ({model}) — {header} ---\n")
        transcript = _get_transcript(character, header)
        session_prompt = _build_session_prompt(
            character, session_field, preamble, header, body, previous_tail, transcript
        )
        session_text = _stream(config, provider, SYSTEM_PROMPT_SESSION, session_prompt)
        if session_text.strip():
            chapters.append(f"## {header}\n\n{session_text}")
            previous_tail = _last_paragraph(session_text)

    full_text = "\n\n---\n\n".join(c for c in chapters if c.strip())
    saved_path = _save_narration(character, model, full_text)
    if saved_path:
        print(f"\n[Narrator] Saved to {saved_path.relative_to(saved_path.parent.parent.parent)}")
