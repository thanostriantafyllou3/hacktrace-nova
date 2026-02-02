"""ElevenLabs text-to-speech for the jury pipeline."""

import os
from typing import Optional

from elevenlabs.client import ElevenLabs
from elevenlabs.play import play


def is_available(config: dict) -> bool:
    """True if TTS is enabled and API key is set."""
    eleven_cfg = config.get("elevenlabs", {}) or {}
    if not eleven_cfg.get("enabled", False):
        return False
    api_key = os.environ.get("ELEVENLABS_API_KEY") or eleven_cfg.get("api_key")
    return bool(api_key)


def _get_client(config: dict):
    """Create ElevenLabs client."""
    eleven_cfg = config.get("elevenlabs", {}) or {}
    api_key = os.environ.get("ELEVENLABS_API_KEY") or eleven_cfg.get("api_key")
    return ElevenLabs(api_key=api_key)


def _get_voice(config: dict, role: str) -> str:
    """Get voice ID for role. Roles: narrator, literal, context, steelman, sceptic, foreperson."""
    eleven_cfg = config.get("elevenlabs", {}) or {}
    voices = eleven_cfg.get("voices", {})
    voice_id = voices.get(role) or voices.get("default") or "EXAVITQu4vr4xnSDxMaL"  # Sarah
    return voice_id


def speak(
    text: str,
    config: dict,
    role: str = "narrator",
) -> bool:
    """
    Speak text via ElevenLabs. Returns True if spoken, False if skipped.
    Truncates very long text to avoid timeout/cost.
    """
    if not text or not text.strip():
        return False
    if not is_available(config):
        return False

    # Truncate to avoid very long generation (e.g. 3000 chars ~ 3-4 min speech)
    max_chars = config.get("elevenlabs", {}).get("max_chars_per_utterance", 2000)
    if len(text) > max_chars:
        text = text[: max_chars - 3].rsplit(".", 1)[0] + "..."

    eleven_cfg = config.get("elevenlabs", {}) or {}
    model_id = eleven_cfg.get("model_id", "eleven_multilingual_v2")
    voice_id = _get_voice(config, role)

    try:
        client = _get_client(config)
        audio = client.text_to_speech.convert(
            text=text.strip(),
            voice_id=voice_id,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
        play(audio)
        return True
    except Exception:
        return False
