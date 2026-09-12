"""Visual Asset Generation Service supporting Pollinations (Flux), Gemini, and procedural fallback."""

import asyncio
import io
import logging
import math
import random
import urllib.parse
from pathlib import Path
from typing import Optional
import aiohttp
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self):
        self.output_dir = settings.TEMP_DIR / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_procedural_cinematic_card(
        self,
        prompt: str,
        on_screen_text: str,
        genre: str,
        width: int,
        height: int,
        output_path: Path
    ) -> Path:
        """Procedural high-aesthetic fallback card generator using PIL."""
        image = Image.new("RGB", (width, height), color=(15, 18, 28))
        draw = ImageDraw.Draw(image)

        # 1. Background gradient based on genre
        if genre == "mythology":
            color_top = (40, 15, 10)
            color_mid = (130, 70, 20)
            color_bot = (10, 5, 5)
            accent_color = (255, 215, 0)
        elif genre == "dark_mystery":
            color_top = (10, 15, 25)
            color_mid = (30, 20, 45)
            color_bot = (5, 5, 10)
            accent_color = (180, 50, 50)
        elif genre == "funny":
            color_top = (255, 110, 50)
            color_mid = (255, 190, 60)
            color_bot = (40, 20, 60)
            accent_color = (255, 255, 255)
        elif genre == "sci_fi":
            color_top = (5, 20, 45)
            color_mid = (10, 80, 120)
            color_bot = (5, 10, 25)
            accent_color = (0, 255, 200)
        else:  # informative
            color_top = (15, 30, 60)
            color_mid = (25, 55, 100)
            color_bot = (10, 15, 30)
            accent_color = (0, 210, 255)

        # Draw vertical gradient
        for y in range(height):
            ratio = y / height
            if ratio < 0.5:
                sub_ratio = ratio * 2
                r = int(color_top[0] * (1 - sub_ratio) + color_mid[0] * sub_ratio)
                g = int(color_top[1] * (1 - sub_ratio) + color_mid[1] * sub_ratio)
                b = int(color_top[2] * (1 - sub_ratio) + color_mid[2] * sub_ratio)
            else:
                sub_ratio = (ratio - 0.5) * 2
                r = int(color_mid[0] * (1 - sub_ratio) + color_bot[0] * sub_ratio)
                g = int(color_mid[1] * (1 - sub_ratio) + color_bot[1] * sub_ratio)
                b = int(color_mid[2] * (1 - sub_ratio) + color_bot[2] * sub_ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Geometric atmospheric background particles / concentric rings
        center_x, center_y = width // 2, height // 2 - 100
        for radius in range(150, min(width, height) // 2 + 100, 70):
            draw.ellipse(
                [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                outline=(*accent_color[:3], 35),
                width=2
            )

        # 3. Add glowing center emblem / abstract icon
        draw.polygon(
            [
                (center_x, center_y - 120),
                (center_x + 100, center_y),
                (center_x, center_y + 120),
                (center_x - 100, center_y)
            ],
            outline=accent_color,
            width=6
        )

        # 4. Text rendering
        # High impact on-screen text banner
        text_banner = on_screen_text.upper()
        bbox = draw.textbbox((0, 0), text_banner)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # Center horizontally in the lower third
        pos_y = height // 2 + 180
        pos_x = (width - text_w) // 2

        # Draw dark contrast box behind text
        pad = 25
        draw.rectangle(
            [pos_x - pad, pos_y - pad, pos_x + text_w + pad, pos_y + text_h + pad],
            fill=(0, 0, 0)
        )
        draw.text((pos_x, pos_y), text_banner, fill=accent_color)

        # Top genre badge
        badge = f"[{genre.upper()} DISCOVERY]"
        draw.text(((width - len(badge) * 8) // 2, 120), badge, fill=(200, 200, 200))

        image.save(output_path, "JPEG", quality=95)
        logger.info(f"Generated procedural aesthetic image -> {output_path}")
        return output_path

    async def generate_image(
        self,
        prompt: str,
        on_screen_text: str = "",
        genre: str = "informative",
        aspect_ratio: str = "9:16",
        output_filename: Optional[str] = None
    ) -> Path:
        """Generate scene visual using Pollinations AI (Flux) with procedural fallback."""
        if not output_filename:
            import uuid
            output_filename = f"scene_{uuid.uuid4().hex[:8]}.jpg"
        output_path = self.output_dir / output_filename

        # Dimensions: standard vertical Shorts (1080x1920) or widescreen (1920x1080)
        width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)

        # If provider is Pollinations (Free Flux AI image generation)
        if settings.IMAGE_PROVIDER == "pollinations":
            try:
                clean_prompt = urllib.parse.quote(f"{prompt}, high quality, sharp focus, 8k")
                url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&model=flux&nologo=true"
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(output_path, "wb") as f:
                                f.write(content)
                            logger.info(f"Downloaded AI generated image via Pollinations -> {output_path}")
                            return output_path
                        else:
                            logger.warning(f"Pollinations returned status {resp.status}. Using procedural fallback.")
            except Exception as e:
                logger.warning(f"Pollinations generation failed ({e}). Using procedural fallback.")

        # Fallback to procedural card
        return self._generate_procedural_cinematic_card(
            prompt=prompt,
            on_screen_text=on_screen_text,
            genre=genre,
            width=width,
            height=height,
            output_path=output_path
        )

image_service = ImageService()
