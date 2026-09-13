"""TTS Service — Studio-quality narration with multi-provider fallback chain.

Priority:
  gemini-2.5-pro-preview-tts (cinematic, emotional, studio quality)
  -> ElevenLabs eleven_turbo_v2_5 (professional voices, emotion control)
  -> edge-tts (free Microsoft neural voices)
  -> macOS say (absolute fallback)
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── Voice presets ──────────────────────────────────────────────────────────────
ELEVENLABS_VOICES = {
    "adam":    "pNInz6obpgDQGcFmaJgB",   # Deep, authoritative, cinematic
    "antoni":  "ErXwobaYiN019PkySvjV",   # Storytelling, warm
    "bella":   "EXAVITQu4vr4xnSDxMaL",   # Female documentary
    "rachel":  "21m00Tcm4TlvDq8ikWAM",   # Clear, professional
}

GEMINI_TTS_STYLE_INSTRUCTION = (
    "You are a world-class documentary narrator. Speak with measured authority and gravitas. "
    "Pace yourself at the rhythm of a Netflix true-crime documentary. "
    "Emphasize key nouns and statistics with a slight weight in your voice. "
    "Add a micro-pause of 0.3s before revealing shocking facts. "
    "Maintain urgency throughout — this is critical information the listener must hear. "
    "Do NOT sound robotic, cheerful, or corporate."
)


# ──────────────────────────────────────────────────────────────────────────────
# Provider: Gemini 2.5 Pro TTS
# ──────────────────────────────────────────────────────────────────────────────

async def _tts_gemini(text: str, voice_hint: str = "Charon") -> Optional[bytes]:
    """Gemini 2.5 Pro TTS — studio-quality speech with narrative emotion."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(None, lambda: client.models.generate_content(
            model=settings.GEMINI_TTS_MODEL,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_TTS_STYLE_INSTRUCTION,
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_hint)
                    )
                ),
            ),
        ))

        for part in response.candidates[0].content.parts:
            if part.inline_data and "audio" in part.inline_data.mime_type:
                return base64.b64decode(part.inline_data.data)

    except Exception as exc:
        logger.warning("Gemini TTS failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Provider: ElevenLabs
# ──────────────────────────────────────────────────────────────────────────────

async def _tts_elevenlabs(text: str, voice_id: str = "pNInz6obpgDQGcFmaJgB") -> Optional[bytes]:
    """ElevenLabs Turbo v2.5 — professional voice with emotion control."""
    if not settings.ELEVENLABS_API_KEY:
        return None
    try:
        from elevenlabs import ElevenLabs, VoiceSettings  # type: ignore

        client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        loop = asyncio.get_event_loop()

        audio_gen = await loop.run_in_executor(None, lambda: client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_turbo_v2_5",
            voice_settings=VoiceSettings(
                stability=0.45,           # Slightly variable for emotion
                similarity_boost=0.82,    # High consistency to voice profile
                style=0.6,               # Moderate style exaggeration
                use_speaker_boost=True,
            ),
            output_format="mp3_44100_128",
        ))

        buf = io.BytesIO()
        for chunk in audio_gen:
            if chunk:
                buf.write(chunk)
        data = buf.getvalue()
        return data if data else None

    except Exception as exc:
        logger.warning("ElevenLabs TTS failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Provider: edge-tts
# ──────────────────────────────────────────────────────────────────────────────

async def _tts_edge(text: str, voice: str, rate: str, pitch: str) -> Optional[bytes]:
    """Microsoft Edge TTS — free, high-quality neural voices."""
    try:
        import edge_tts  # type: ignore

        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        data = buf.getvalue()
        return data if data else None

    except Exception as exc:
        logger.warning("edge-tts failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Provider: macOS say (absolute fallback)
# ──────────────────────────────────────────────────────────────────────────────

async def _tts_macos_say(text: str, output_path: Path) -> Optional[bytes]:
    """macOS say command — absolute last resort."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "say", "-v", "Alex", "-r", "180", "-o", str(output_path),
            "--data-format=LEF32@44100", text,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=30)
        if output_path.exists():
            return output_path.read_bytes()
    except Exception as exc:
        logger.warning("macOS say failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

class TTSService:
    def __init__(self):
        self._provider_chain = self._build_chain()

    def reload(self):
        """Re-detect TTS providers after settings change."""
        self._provider_chain = self._build_chain()

    def _build_chain(self) -> list:
        provider = settings.TTS_PROVIDER
        chain = []

        if provider == "auto":
            if settings.GEMINI_API_KEY:
                chain.append("gemini-tts")
            if settings.ELEVENLABS_API_KEY:
                chain.append("elevenlabs")
            chain.extend(["edge-tts", "macos-say"])
        elif provider == "gemini-tts":
            chain = ["gemini-tts", "edge-tts", "macos-say"]
        elif provider == "elevenlabs":
            chain = ["elevenlabs", "edge-tts", "macos-say"]
        elif provider == "edge-tts":
            chain = ["edge-tts", "macos-say"]
        else:
            chain = ["edge-tts", "macos-say"]

        logger.info("TTS provider chain: %s", chain)
        return chain

    @property
    def active_provider(self) -> str:
        return self._provider_chain[0] if self._provider_chain else "macos-say"

    async def synthesize(
        self,
        text: str,
        voice_name: str = "",
        rate: str = "",
        pitch: str = "",
        output_path: Optional[Path] = None,
    ) -> Path:
        """Synthesize speech and return path to audio file."""
        voice = voice_name or settings.DEFAULT_VOICE
        speech_rate = rate or settings.TTS_SPEECH_RATE
        speech_pitch = pitch or settings.TTS_SPEECH_PITCH

        if output_path is None:
            output_path = settings.TEMP_DIR / f"tts_{hash(text) & 0xFFFFFF:06x}.mp3"

        audio_bytes: Optional[bytes] = None

        for p in self._provider_chain:
            logger.info("Trying TTS provider: %s", p)

            if p == "gemini-tts":
                audio_bytes = await _tts_gemini(text, voice_hint="Charon")
            elif p == "elevenlabs":
                el_voice = ELEVENLABS_VOICES.get("adam", ELEVENLABS_VOICES["adam"])
                audio_bytes = await _tts_elevenlabs(text, voice_id=el_voice)
            elif p == "edge-tts":
                audio_bytes = await _tts_edge(text, voice, speech_rate, speech_pitch)
            elif p == "macos-say":
                wav_path = output_path.with_suffix(".aiff")
                audio_bytes = await _tts_macos_say(text, wav_path)

            if audio_bytes:
                logger.info("TTS via %s (%d bytes)", p, len(audio_bytes))
                break

        if not audio_bytes:
            logger.error("All TTS providers failed for: %s", text[:50])
            # Generate 1s silence
            audio_bytes = _generate_silence()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        return output_path


def _generate_silence(duration_ms: int = 1000) -> bytes:
    """Generate silent MP3 bytes."""
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * (44100 * duration_ms // 1000))
    return buf.getvalue()


# Singleton
tts_service = TTSService()
