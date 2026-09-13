"""Image Service — Multi-provider cinematic image generation.

Priority chain:
  gemini-3-pro-image-preview (4K grounded, primary paid)
  -> imagen-4.0-ultra-generate-001 (ultra photorealistic, fallback paid)
  -> replicate/flux-1.1-pro (alternative paid, $0.04/img)
  -> pollinations.ai (free Flux)
  -> procedural gradient (absolute fallback)
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import List, Optional

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Cinematic prompt enhancer
# ──────────────────────────────────────────────────────────────────────────────

CINEMATIC_SUFFIX = (
    ", photorealistic, 8K UHD, cinematic lighting, sharp focus, depth of field, "
    "professional photography, no text, no watermarks, no logos"
)

STYLE_ENHANCERS = {
    "informative": "educational documentary style, dramatic natural lighting, ",
    "horror": "dark atmospheric horror, deep shadows, ominous fog, chiaroscuro, ",
    "motivational": "golden hour lighting, epic wide angle, inspirational atmosphere, ",
    "comedy": "bright colorful lighting, vivid saturation, playful composition, ",
    "thriller": "cold blue tones, high contrast, tension-filled atmosphere, ",
    "documentary": "raw photojournalism style, natural light, authentic emotion, ",
    "mystery": "noir aesthetic, shadows and highlights, moody atmosphere, ",
    "scientific": "clean studio look, crisp detail, scientific illustration quality, ",
}


def _enhance_prompt(prompt: str, genre: str = "informative", aspect: str = "9:16") -> str:
    style = STYLE_ENHANCERS.get(genre, STYLE_ENHANCERS["informative"])
    orientation = "vertical portrait format" if aspect == "9:16" else "horizontal landscape format"
    return f"{style}{prompt}{CINEMATIC_SUFFIX}, {orientation}"


# ──────────────────────────────────────────────────────────────────────────────
# Provider: Gemini 3 Pro Image (primary paid)
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_gemini3_image(prompt: str, aspect: str) -> Optional[bytes]:
    """Use gemini-3-pro-image-preview via Interactions API for 4K grounded images."""
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        image_size = "4K" if aspect == "16:9" else "2K"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.interactions.create(
            model=settings.GEMINI_IMAGE_MODEL,
            input=prompt,
            response_format={
                "type": "image",
                "aspect_ratio": aspect,
                "image_size": image_size,
            },
        ))
        if response.output_image and response.output_image.data:
            return base64.b64decode(response.output_image.data)
    except Exception as exc:
        logger.warning("Gemini 3 image failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Provider: Imagen 4 Ultra (fallback paid)
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_imagen_ultra(prompt: str, aspect: str) -> Optional[bytes]:
    """Use Imagen 4 Ultra for ultra-photorealistic generation."""
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.models.generate_images(
            model=settings.IMAGEN_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect,
            ),
        ))
        if response.generated_images:
            img = response.generated_images[0].image
            if img.image_bytes:
                return img.image_bytes
    except Exception as exc:
        logger.warning("Imagen Ultra failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Provider: Replicate Flux 1.1 Pro (alternative paid)
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_replicate_flux(prompt: str, aspect: str) -> Optional[bytes]:
    """Use Replicate Flux 1.1 Pro — ~$0.04/image."""
    if not settings.REPLICATE_API_TOKEN:
        return None
    try:
        width, height = (1080, 1920) if aspect == "9:16" else (1920, 1080)
        async with aiohttp.ClientSession() as session:
            # Start prediction
            async with session.post(
                f"https://api.replicate.com/v1/models/{settings.REPLICATE_IMAGE_MODEL}/predictions",
                json={"input": {"prompt": prompt, "width": width, "height": height,
                                "num_outputs": 1, "output_format": "jpg"}},
                headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
                         "Content-Type": "application/json"},
            ) as r:
                data = await r.json()
                prediction_id = data.get("id")

            if not prediction_id:
                return None

            # Poll for completion
            for _ in range(60):
                await asyncio.sleep(2)
                async with session.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"},
                ) as r:
                    pred = await r.json()
                    status = pred.get("status")
                    if status == "succeeded":
                        url = pred["output"][0]
                        async with session.get(url) as img_r:
                            return await img_r.read()
                    elif status in ("failed", "canceled"):
                        break

    except Exception as exc:
        logger.warning("Replicate Flux failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Provider: Pollinations (free Flux)
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_pollinations(prompt: str, aspect: str) -> Optional[bytes]:
    """Free Flux generation via Pollinations.ai."""
    try:
        width, height = (1080, 1920) if aspect == "9:16" else (1920, 1080)
        encoded = urllib.parse.quote(prompt[:400])
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&enhance=true"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=45)) as r:
                if r.status == 200:
                    return await r.read()
    except Exception as exc:
        logger.warning("Pollinations failed: %s", exc)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Provider: Procedural gradient (absolute fallback)
# ──────────────────────────────────────────────────────────────────────────────

GENRE_GRADIENTS = {
    "informative": [(15, 32, 79), (32, 178, 170)],
    "horror": [(10, 10, 10), (80, 0, 0)],
    "motivational": [(255, 165, 0), (255, 69, 0)],
    "comedy": [(255, 214, 0), (255, 105, 180)],
    "thriller": [(20, 20, 40), (0, 100, 150)],
    "documentary": [(30, 30, 30), (80, 80, 80)],
    "mystery": [(10, 10, 30), (60, 0, 80)],
    "scientific": [(0, 50, 100), (0, 180, 200)],
}


def _generate_procedural(prompt: str, genre: str, aspect: str) -> bytes:
    """Procedural gradient image with text overlay as absolute fallback."""
    w, h = (1080, 1920) if aspect == "9:16" else (1920, 1080)
    colors = GENRE_GRADIENTS.get(genre, GENRE_GRADIENTS["informative"])
    c1, c2 = colors[0], colors[1]

    img = Image.new("RGB", (w, h))
    pixels = img.load()
    for y in range(h):
        t = y / h
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        for x in range(w):
            pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)
    words = prompt[:60].split()
    wrapped = " ".join(words[:8]) + ("\n" + " ".join(words[8:16]) if len(words) > 8 else "")
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=w // 18)
    except Exception:
        font = ImageFont.load_default()

    # Shadow + text
    draw.text((w // 2 + 3, h // 2 + 3), wrapped, fill=(0, 0, 0, 180), font=font, anchor="mm", align="center")
    draw.text((w // 2, h // 2), wrapped, fill=(255, 255, 255), font=font, anchor="mm", align="center")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

class ImageService:
    def __init__(self):
        self._provider_chain = self._build_chain()

    def reload(self):
        """Re-detect image providers after settings change."""
        self._provider_chain = self._build_chain()

    def _build_chain(self) -> List[str]:
        chain = []
        provider = settings.IMAGE_PROVIDER

        if provider == "auto":
            if settings.GEMINI_API_KEY:
                chain.append("gemini3")
                chain.append("imagen")
            if settings.REPLICATE_API_TOKEN:
                chain.append("replicate")
            chain.append("pollinations")
            chain.append("procedural")
        elif provider == "gemini-3" and settings.GEMINI_API_KEY:
            chain = ["gemini3", "imagen", "pollinations", "procedural"]
        elif provider == "imagen-ultra" and settings.GEMINI_API_KEY:
            chain = ["imagen", "pollinations", "procedural"]
        elif provider == "replicate" and settings.REPLICATE_API_TOKEN:
            chain = ["replicate", "pollinations", "procedural"]
        else:
            chain = ["pollinations", "procedural"]

        logger.info("Image provider chain: %s", chain)
        return chain

    @property
    def active_provider(self) -> str:
        return self._provider_chain[0] if self._provider_chain else "procedural"

    async def generate_scene_image(
        self,
        prompt: str,
        genre: str = "informative",
        aspect: str = "9:16",
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Generate a single scene image and save to disk."""
        enhanced = _enhance_prompt(prompt, genre, aspect)
        image_bytes: Optional[bytes] = None

        for provider in self._provider_chain:
            logger.info("Trying image provider: %s", provider)
            if provider == "gemini3":
                image_bytes = await _generate_gemini3_image(enhanced, aspect)
            elif provider == "imagen":
                image_bytes = await _generate_imagen_ultra(enhanced, aspect)
            elif provider == "replicate":
                image_bytes = await _generate_replicate_flux(enhanced, aspect)
            elif provider == "pollinations":
                image_bytes = await _generate_pollinations(enhanced, aspect)
            elif provider == "procedural":
                image_bytes = _generate_procedural(prompt, genre, aspect)

            if image_bytes:
                logger.info("Image generated via: %s (%d bytes)", provider, len(image_bytes))
                break

        if not image_bytes:
            image_bytes = _generate_procedural(prompt, genre, aspect)

        out_dir = output_dir or settings.TEMP_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"scene_{uuid.uuid4().hex[:8]}.jpg"

        # Convert to consistent JPEG format
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.save(str(path), format="JPEG", quality=92)

        return path

    async def generate_multi_cut_images(
        self,
        primary_prompt: str,
        sub_clip_prompts: List[str],
        genre: str = "informative",
        aspect: str = "9:16",
        output_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Generate multiple images for a single scene (multi-cut editing)."""
        prompts = [primary_prompt] + sub_clip_prompts[:2]  # Max 3 images per scene
        tasks = [self.generate_scene_image(p, genre, aspect, output_dir) for p in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        paths = []
        for r in results:
            if isinstance(r, Path):
                paths.append(r)

        # Always return at least one image
        if not paths:
            paths.append(await self.generate_scene_image(primary_prompt, genre, aspect, output_dir))

        return paths


# Singleton
image_service = ImageService()
