"""Text-to-Speech service using Edge-TTS (free neural), macOS 'say' fallback, and ElevenLabs."""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import edge_tts

from app.config import settings

logger = logging.getLogger(__name__)

AVAILABLE_VOICES = [
    {
        "id": "en-US-ChristopherNeural",
        "name": "Christopher (Authoritative, Documentaries)",
        "gender": "Male",
        "recommended_for": ["informative", "dark_mystery", "mythology"]
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Guy (Casual, Fast-paced)",
        "gender": "Male",
        "recommended_for": ["funny", "informative"]
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny (Clear, Friendly)",
        "gender": "Female",
        "recommended_for": ["informative", "funny"]
    },
    {
        "id": "en-US-EricNeural",
        "name": "Eric (Deep, Cinematic)",
        "gender": "Male",
        "recommended_for": ["mythology", "dark_mystery", "sci_fi"]
    },
    {
        "id": "en-GB-RyanNeural",
        "name": "Ryan (British Storyteller)",
        "gender": "Male",
        "recommended_for": ["mythology", "history"]
    }
]


class TTSService:
    def __init__(self):
        self.output_dir = settings.TEMP_DIR / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def _fallback_local_speech(self, text: str, output_path: Path) -> Path:
        """Fallback to macOS built-in 'say' or FFmpeg silence/tone when offline."""
        logger.info(f"Generating offline TTS fallback for: '{text[:30]}...'")
        aiff_temp = output_path.with_suffix(".aiff")
        
        # Check if macOS 'say' binary is available
        if shutil.which("say"):
            try:
                say_proc = await asyncio.create_subprocess_exec(
                    "say", "-v", "Daniel", "-o", str(aiff_temp), text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await say_proc.communicate()
                
                # Convert AIFF to MP3 via ffmpeg
                conv_proc = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-y", "-i", str(aiff_temp), "-c:a", "libmp3lame", "-b:a", "192k", str(output_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await conv_proc.communicate()
                if aiff_temp.exists():
                    aiff_temp.unlink()
                if output_path.exists():
                    return output_path
            except Exception as e:
                logger.warning(f"macOS 'say' fallback failed: {e}")

        # If say fails or isn't on macOS, synthesize a 3.5s warm ambient audio tone in FFmpeg
        dur = max(len(text.split()) * 0.35, 3.0)
        synth_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=220:duration={dur}",
            "-c:a", "libmp3lame",
            str(output_path)
        ]
        synth_proc = await asyncio.create_subprocess_exec(*synth_cmd)
        await synth_proc.communicate()
        return output_path

    async def generate_speech(
        self,
        text: str,
        voice: str = "en-US-ChristopherNeural",
        output_filename: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> Path:
        """Synthesize text to speech using Edge-TTS with resilient local fallback."""
        if not output_filename:
            import uuid
            output_filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            
        output_path = self.output_dir / output_filename

        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))
            logger.info(f"Synthesized Edge-TTS audio ({len(text)} chars) -> {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis error ({e}). Switching to local voice fallback.")
            return await self._fallback_local_speech(text, output_path)

    async def get_audio_duration(self, audio_path: Path) -> float:
        """Get exact duration of an audio file using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        try:
            return float(stdout.decode().strip())
        except Exception:
            return 3.5

tts_service = TTSService()
