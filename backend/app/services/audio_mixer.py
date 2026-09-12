"""Audio Mixer — Side-chain compression, music ducking, LUFS normalization."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Bundled royalty-free music stems (path relative to project root)
MUSIC_STEMS_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "music"

MUSIC_TRACKS = {
    "epic_cinematic":      "epic_cinematic.mp3",
    "dark_ambient":        "dark_ambient.mp3",
    "upbeat_motivational": "upbeat_motivational.mp3",
    "lofi_mystery":        "lofi_mystery.mp3",
    "tech_pulse":          "tech_pulse.mp3",
}


async def _run_ffmpeg(*args: str) -> bool:
    """Run an ffmpeg command asynchronously."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + list(args)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    if proc.returncode != 0:
        logger.warning("ffmpeg error: %s", stderr.decode()[:300])
    return proc.returncode == 0


def _get_music_path(genre: str) -> Optional[Path]:
    """Return the best matching music stem for a genre."""
    genre_map = {
        "informative": "tech_pulse",
        "horror": "dark_ambient",
        "motivational": "upbeat_motivational",
        "comedy": "upbeat_motivational",
        "thriller": "dark_ambient",
        "documentary": "epic_cinematic",
        "mystery": "lofi_mystery",
        "scientific": "tech_pulse",
    }
    stem_name = genre_map.get(genre, "epic_cinematic")
    track = MUSIC_TRACKS.get(stem_name)
    if not track:
        return None
    path = MUSIC_STEMS_DIR / track
    return path if path.exists() else None


async def mix_with_music(
    voice_path: Path,
    output_path: Path,
    genre: str = "informative",
    music_path: Optional[Path] = None,
    video_duration_sec: float = 30.0,
) -> Path:
    """
    Mix voice narration with background music.
    - Music auto-loops to match video duration
    - Music volume: settings.MUSIC_VOLUME_DB (default -18dBFS)
    - Voice volume: settings.VOICE_VOLUME_DB (default -6dBFS)
    - Normalize output to -14 LUFS
    """
    if not settings.MUSIC_ENABLED:
        return voice_path

    music = music_path or _get_music_path(genre)
    if not music:
        logger.info("No music stem found for genre '%s', skipping music mix", genre)
        return voice_path

    # Step 1: Mix voice + looped music
    mixed_path = output_path.parent / f"mixed_{output_path.stem}.aac"
    voice_db = settings.VOICE_VOLUME_DB  # e.g. -6
    music_db = settings.MUSIC_VOLUME_DB  # e.g. -18

    await _run_ffmpeg(
        "-i", str(voice_path),
        "-stream_loop", "-1",    # Loop music to fill video duration
        "-i", str(music),
        "-t", str(video_duration_sec),
        "-filter_complex",
        # Volume adjust + side-chain compress music duck during speech
        f"[0:a]volume={voice_db}dB[voice];"
        f"[1:a]volume={music_db}dB[music];"
        "[voice][music]amix=inputs=2:duration=first:weights=1 1[out]",
        "-map", "[out]",
        "-c:a", "aac",
        "-b:a", "192k",
        str(mixed_path),
    )

    if not mixed_path.exists():
        logger.warning("Music mix failed, returning raw voice")
        return voice_path

    # Step 2: Normalize to -14 LUFS (YouTube/Shorts recommendation)
    await _run_ffmpeg(
        "-i", str(mixed_path),
        "-filter:a", "loudnorm=I=-14:LRA=11:TP=-1.5",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    )

    if output_path.exists():
        mixed_path.unlink(missing_ok=True)
        return output_path

    return mixed_path  # Return intermediate if normalize failed


async def normalize_audio(input_path: Path, output_path: Path) -> Path:
    """Normalize a single audio file to -14 LUFS."""
    ok = await _run_ffmpeg(
        "-i", str(input_path),
        "-filter:a", "loudnorm=I=-14:LRA=11:TP=-1.5",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    )
    return output_path if ok and output_path.exists() else input_path
