"""Test end-to-end video synthesis pipeline (TTS + Image + FFmpeg + Subtitles)."""

import asyncio
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.video_engine import video_engine
from app.schemas.video import SubtitleStyle


async def main():
    print("Testing Video Engine Pipeline...")
    
    mock_script = {
        "title": "Roman Concrete Secret",
        "genre": "mythology",
        "aspect_ratio": "9:16",
        "scenes": [
            {
                "scene_id": 1,
                "voiceover_text": "Ancient Romans had a secret recipe for concrete that actually heals itself.",
                "on_screen_text": "SELF-HEALING CONCRETE",
                "visual_prompt": "Ancient Roman ruins with glowing self healing marble fractures, cinematic mist, 9:16 vertical smartphone format",
                "camera_motion": "zoom_in",
            },
            {
                "scene_id": 2,
                "voiceover_text": "Modern scientists only discovered why: quicklime triggers a chemical reaction whenever rainwater seeps inside.",
                "on_screen_text": "THE CHEMICAL SECRET",
                "visual_prompt": "Macro shot of lime clasts reacting with water inside stone, glowing blue minerals, 9:16 vertical smartphone format",
                "camera_motion": "pan_left",
            },
            {
                "scene_id": 3,
                "voiceover_text": "Subscribe to discover more forgotten ancient technology.",
                "on_screen_text": "SUBSCRIBE NOW",
                "visual_prompt": "Golden Roman coin rotating in mid air against dark ancient temple backdrop, 9:16 vertical smartphone format",
                "camera_motion": "zoom_out",
            }
        ]
    }
    
    output_video = await video_engine.assemble_full_video(
        script_dict=mock_script,
        voice_name="en-US-ChristopherNeural",
        aspect_ratio="9:16",
        subtitle_style=SubtitleStyle.HORMOZI_BOLD,
        burn_subtitles=True
    )
    
    print(f"\nFinal Video Generated Successfully!")
    print(f"File Path: {output_video}")
    print(f"File Size: {output_video.stat().st_size / 1024 / 1024:.2f} MB")
    assert output_video.exists(), "Output video file should exist"
    assert output_video.stat().st_size > 50000, "Output video should be non-trivial size"
    print("All Video Pipeline tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
