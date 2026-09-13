"""AI Video Service — Multi-engine generative video synthesis.

Supported Engines:
  - gemini_omni: Google Gemini Omni 1.1 Flash (`gemini-omni-1.1-flash`) via official google-genai Interactions API
  - minimax: MiniMax Video-01 (Hailuo AI) via Replicate API
  - luma: Luma Ray-2 via Replicate API
  - fast_motion: 2.5D Camera Physics via FFmpeg zoompan
  - hybrid: AI Video for critical Hook & Climax + 2.5D for transitions
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import tempfile
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


def _sanitize_error(err: Exception | str) -> str:
    """Redacts API keys and long URLs from error messages."""
    msg = str(err)
    if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 6:
        msg = msg.replace(settings.GEMINI_API_KEY, "[REDACTED_GEMINI_KEY]")
    if settings.REPLICATE_API_TOKEN and len(settings.REPLICATE_API_TOKEN) > 6:
        msg = msg.replace(settings.REPLICATE_API_TOKEN, "[REDACTED_REPLICATE_KEY]")
    msg = re.sub(r"AIza[0-9A-Za-z_\-]{30,}", "[REDACTED_KEY]", msg)
    msg = re.sub(r"r8_[0-9A-Za-z]{30,}", "[REDACTED_KEY]", msg)
    return msg[:300]


# ──────────────────────────────────────────────────────────────────────────────
# Google Gemini Omni 1.1 Flash Video Provider
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_gemini_omni_video(
    prompt: str,
    first_frame_path: Optional[Path] = None,
    aspect_ratio: str = "9:16",
    duration_sec: int = 4,
    resolution: str = "720p",
    timeout_sec: int = 180,
    output_path: Optional[Path] = None,
) -> Optional[Path]:
    """Generates a video clip using Google Gemini Omni 1.1 Flash via the official google-genai SDK."""
    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini Omni Video requested but GEMINI_API_KEY is not set.")
        return None

    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=timeout_sec * 1000),
        )

        input_parts: List[Dict[str, Any]] = []

        # 1. Upload first frame for Image-to-Video consistency if provided
        if first_frame_path and first_frame_path.exists():
            try:
                loop = asyncio.get_event_loop()
                uploaded_file = await loop.run_in_executor(
                    None,
                    lambda: client.files.upload(file=str(first_frame_path))
                )
                input_parts.append({
                    "type": "image",
                    "uri": uploaded_file.uri,
                    "mime_type": uploaded_file.mime_type or "image/png",
                })
                # Add first frame tag
                prompt_formatted = f"<FIRST_FRAME> {prompt}"
            except Exception as up_err:
                logger.warning("Failed to upload first frame to Gemini Files API: %s; falling back to text-only", up_err)
                prompt_formatted = prompt
        else:
            prompt_formatted = prompt

        input_parts.append({
            "type": "text",
            "text": prompt_formatted,
        })

        # Video response format
        clip_duration = min(max(int(duration_sec), 3), 10)  # Gemini Omni supports 3-10s
        video_config = {
            "type": "video",
            "delivery": "uri",
            "aspect_ratio": aspect_ratio,
            "duration": clip_duration,
            "resolution": resolution,
        }

        loop = asyncio.get_event_loop()
        logger.info("Calling Gemini Omni Flash video generation for prompt: '%s' (duration=%ds, aspect=%s)",
                    prompt[:60], clip_duration, aspect_ratio)

        interaction = await loop.run_in_executor(
            None,
            lambda: client.interactions.create(
                model=getattr(settings, "AI_VIDEO_MODEL", "gemini-omni-1.1-flash"),
                input=input_parts,
                response_format=video_config,
            )
        )

        output_video = getattr(interaction, "output_video", None)
        if not output_video or not output_video.uri:
            logger.warning("No video URI in Gemini Omni response.")
            return None

        video_uri = output_video.uri
        if output_path is None:
            output_path = settings.TEMP_DIR / f"omni_{interaction.id or uuid.uuid4().hex[:6]}.mp4"

        # Download the video bytes
        headers = {"x-goog-api-key": settings.GEMINI_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(video_uri, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    output_path.write_bytes(data)
                    logger.info("Gemini Omni video saved to %s (%d bytes)", output_path, len(data))
                    return output_path
                else:
                    logger.warning("Gemini Omni video download returned status %d", resp.status)

    except Exception as exc:
        logger.warning("Gemini Omni Flash video generation failed: %s", _sanitize_error(exc))

    return None


# ──────────────────────────────────────────────────────────────────────────────
# MiniMax Video-01 Provider (via Replicate API)
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_minimax_video(
    prompt: str,
    first_frame_path: Optional[Path] = None,
    aspect_ratio: str = "9:16",
    output_path: Optional[Path] = None,
) -> Optional[Path]:
    """Generates a video clip using MiniMax Video-01 via the Replicate API."""
    if not settings.REPLICATE_API_TOKEN:
        logger.warning("MiniMax video requested but REPLICATE_API_TOKEN is not set.")
        return None

    try:
        import replicate  # type: ignore

        os.environ["REPLICATE_API_TOKEN"] = settings.REPLICATE_API_TOKEN
        loop = asyncio.get_event_loop()

        input_params: Dict[str, Any] = {
            "prompt": prompt,
            "prompt_optimizer": True,
        }

        # If first frame provided, pass as file handle for Image-to-Video
        if first_frame_path and first_frame_path.exists():
            input_params["first_frame_image"] = open(first_frame_path, "rb")

        logger.info("Calling Replicate minimax/video-01 for prompt: '%s'", prompt[:60])

        output = await loop.run_in_executor(
            None,
            lambda: replicate.run("minimax/video-01", input=input_params)
        )

        video_url = str(output)
        if output_path is None:
            output_path = settings.TEMP_DIR / f"minimax_{uuid.uuid4().hex[:6]}.mp4"

        async with aiohttp.ClientSession() as session:
            async with session.get(video_url, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    output_path.write_bytes(data)
                    logger.info("MiniMax video saved to %s (%d bytes)", output_path, len(data))
                    return output_path

    except Exception as exc:
        logger.warning("MiniMax video generation failed: %s", _sanitize_error(exc))

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Luma Dream Machine / Ray Provider (via Replicate API)
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_luma_video(
    prompt: str,
    first_frame_path: Optional[Path] = None,
    aspect_ratio: str = "9:16",
    output_path: Optional[Path] = None,
) -> Optional[Path]:
    """Generates a video clip using Luma Ray via the Replicate API."""
    if not settings.REPLICATE_API_TOKEN:
        logger.warning("Luma video requested but REPLICATE_API_TOKEN is not set.")
        return None

    try:
        import replicate  # type: ignore

        os.environ["REPLICATE_API_TOKEN"] = settings.REPLICATE_API_TOKEN
        loop = asyncio.get_event_loop()

        input_params: Dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "loop": False,
        }

        if first_frame_path and first_frame_path.exists():
            input_params["start_image"] = open(first_frame_path, "rb")

        logger.info("Calling Replicate luma/ray for prompt: '%s'", prompt[:60])

        output = await loop.run_in_executor(
            None,
            lambda: replicate.run("luma/ray", input=input_params)
        )

        video_url = str(output)
        if output_path is None:
            output_path = settings.TEMP_DIR / f"luma_{uuid.uuid4().hex[:6]}.mp4"

        async with aiohttp.ClientSession() as session:
            async with session.get(video_url, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    output_path.write_bytes(data)
                    logger.info("Luma video saved to %s (%d bytes)", output_path, len(data))
                    return output_path

    except Exception as exc:
        logger.warning("Luma video generation failed: %s", _sanitize_error(exc))

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Public AI Video Service
# ──────────────────────────────────────────────────────────────────────────────

class AIVideoService:
    def __init__(self):
        self.reload()

    def reload(self):
        """Refreshes active status based on current settings."""
        self.has_gemini = bool(settings.GEMINI_API_KEY)
        self.has_replicate = bool(settings.REPLICATE_API_TOKEN)

    def get_available_engines(self) -> List[Dict[str, Any]]:
        """Returns list of video engines with live availability status."""
        return [
            {
                "id": "fast_motion",
                "label": "Fast Motion Reel (2.5D)",
                "engine": "FFmpeg Ken Burns Physics",
                "description": "Instant render (~20s). High-res AI keyframes + cinematic zooms, pans, and whip cuts.",
                "type": "2.5d_motion",
                "speed": "~20 seconds total",
                "cost": "$0.00 / Free",
                "is_available": True,
                "badge": "Instant & Free",
            },
            {
                "id": "gemini_omni",
                "label": "Google Gemini Omni / Veo",
                "engine": "gemini-omni-1.1-flash",
                "description": "True generative AI video with native 9:16 vertical format, fluid motion, and image-to-video consistency.",
                "type": "true_ai_video",
                "speed": "~45-75s per scene",
                "cost": "~$0.05-0.15 / clip",
                "is_available": self.has_gemini,
                "requires": "Google Gemini API Key",
                "badge": "Ready" if self.has_gemini else "Key Required",
            },
            {
                "id": "minimax",
                "label": "MiniMax Video-01 (Hailuo AI)",
                "engine": "minimax/video-01 via Replicate",
                "description": "Photorealistic human motion, expressive faces, dramatic cinematic camera moves.",
                "type": "true_ai_video",
                "speed": "~60s per scene",
                "cost": "~$0.05 / clip",
                "is_available": self.has_replicate,
                "requires": "Replicate API Token",
                "badge": "Ready" if self.has_replicate else "Token Required",
            },
            {
                "id": "luma",
                "label": "Luma Dream Machine (Ray)",
                "engine": "luma/ray via Replicate",
                "description": "Fluid natural physics, volumetric lighting, atmospheric environments, and smooth camera flights.",
                "type": "true_ai_video",
                "speed": "~45s per scene",
                "cost": "~$0.10 / clip",
                "is_available": self.has_replicate,
                "requires": "Replicate API Token",
                "badge": "Ready" if self.has_replicate else "Token Required",
            },
            {
                "id": "hybrid",
                "label": "Hybrid Cinema Reel",
                "engine": "AI Video (Hook & Climax) + 2.5D Transitions",
                "description": "True AI Video for Scene 1 (the vital 3s hook) and turning point, with fast 2.5D motion for transitions.",
                "type": "hybrid",
                "speed": "~1-2 minutes total",
                "cost": "~$0.10-0.20 total",
                "is_available": self.has_gemini or self.has_replicate,
                "requires": "Gemini Key or Replicate Token",
                "badge": "Recommended",
            },
        ]

    async def generate_scene_video(
        self,
        prompt: str,
        engine_id: str = "fast_motion",
        first_frame_path: Optional[Path] = None,
        aspect_ratio: str = "9:16",
        duration_sec: int = 4,
        resolution: str = "720p",
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """Generates a video clip using the requested AI engine, or returns None to fallback to 2.5D motion."""
        if engine_id in ("fast_motion", "none"):
            return None

        effective_engine = engine_id
        if engine_id == "hybrid":
            if self.has_gemini:
                effective_engine = "gemini_omni"
            elif self.has_replicate:
                effective_engine = "minimax"
            else:
                return None

        out_path = None
        if output_dir:
            out_path = output_dir / f"ai_video_{uuid.uuid4().hex[:6]}.mp4"

        if effective_engine == "gemini_omni":
            return await _generate_gemini_omni_video(
                prompt=prompt,
                first_frame_path=first_frame_path,
                aspect_ratio=aspect_ratio,
                duration_sec=duration_sec,
                resolution=resolution,
                output_path=out_path,
            )
        elif effective_engine == "minimax":
            return await _generate_minimax_video(
                prompt=prompt,
                first_frame_path=first_frame_path,
                aspect_ratio=aspect_ratio,
                output_path=out_path,
            )
        elif effective_engine == "luma":
            return await _generate_luma_video(
                prompt=prompt,
                first_frame_path=first_frame_path,
                aspect_ratio=aspect_ratio,
                output_path=out_path,
            )

        return None


ai_video_service = AIVideoService()
