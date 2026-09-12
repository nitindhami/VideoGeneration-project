"""FFmpeg Video Engine: Dynamic Ken Burns motion, scene assembly, and subtitle burning."""

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.config import settings
from app.schemas.video import SubtitleStyle, VideoAspect
from app.services.tts_service import tts_service
from app.services.image_service import image_service
from app.services.subtitle_engine import subtitle_engine

logger = logging.getLogger(__name__)


class VideoEngine:
    def __init__(self):
        self.output_dir = settings.OUTPUT_DIR
        self.temp_dir = settings.TEMP_DIR / "renders"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def _render_scene_clip(
        self,
        image_path: Path,
        audio_path: Path,
        duration: float,
        camera_motion: str,
        aspect_ratio: str,
        output_path: Path
    ) -> Path:
        """Render a single scene image into a video clip with dynamic pan/zoom motion."""
        width = 1080 if aspect_ratio == "9:16" else 1920
        height = 1920 if aspect_ratio == "9:16" else 1080
        fps = 30
        total_frames = int(max(duration, 1.0) * fps)

        # Build zoompan filter based on camera motion
        if camera_motion == "zoom_out":
            zoom_expr = "max(1.2-0.0015*on,1.0)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif camera_motion == "pan_left":
            zoom_expr = "1.15"
            x_expr = f"min((iw-iw/zoom)*(on/{total_frames}),iw-iw/zoom)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif camera_motion == "pan_right":
            zoom_expr = "1.15"
            x_expr = f"max((iw-iw/zoom)*(1-on/{total_frames}),0)"
            y_expr = "ih/2-(ih/zoom/2)"
        else:  # default zoom_in
            zoom_expr = "min(zoom+0.0015,1.25)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"

        filter_str = (
            f"scale=8000:-1,"
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s={width}x{height}:fps={fps},"
            f"format=yuv420p"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{duration:.3f}",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]

        logger.info(f"Rendering scene clip: motion={camera_motion}, dur={duration:.2f}s -> {output_path.name}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"FFmpeg scene render error: {stderr.decode()[:300]}")
            # Fallback simple scale without zoompan if complex zoompan fails
            fallback_cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(image_path),
                "-i", str(audio_path),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},format=yuv420p",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                "-t", f"{duration:.3f}",
                str(output_path)
            ]
            fallback_proc = await asyncio.create_subprocess_exec(*fallback_cmd)
            await fallback_proc.communicate()

        return output_path

    async def assemble_full_video(
        self,
        script_dict: Dict[str, Any],
        voice_name: str = "en-US-ChristopherNeural",
        aspect_ratio: str = "9:16",
        subtitle_style: SubtitleStyle = SubtitleStyle.HORMOZI_BOLD,
        burn_subtitles: bool = True
    ) -> Path:
        """Full pipeline: TTS -> Images -> Scene Clips -> Concat -> Burn Subtitles -> Final MP4."""
        job_id = uuid.uuid4().hex[:8]
        job_temp = self.temp_dir / f"job_{job_id}"
        job_temp.mkdir(parents=True, exist_ok=True)

        scenes = script_dict.get("scenes", [])
        genre = script_dict.get("genre", "informative")
        clip_paths: List[Path] = []
        enriched_scenes: List[Dict[str, Any]] = []

        cumulative_time = 0.0

        # 1. Generate audio & visuals for each scene concurrently
        for idx, sc in enumerate(scenes, start=1):
            voiceover = sc.get("voiceover_text", "")
            on_screen = sc.get("on_screen_text", "")
            v_prompt = sc.get("visual_prompt", "")
            motion = sc.get("camera_motion", "zoom_in")

            # Synthesize Audio
            audio_path = await tts_service.generate_speech(
                text=voiceover,
                voice=voice_name,
                output_filename=f"job_{job_id}_scene_{idx}.mp3"
            )
            actual_duration = await tts_service.get_audio_duration(audio_path)
            # Add small 0.3s breathing room at the end of each scene
            scene_duration = max(actual_duration + 0.3, 2.5)

            # Generate Image
            image_path = await image_service.generate_image(
                prompt=v_prompt,
                on_screen_text=on_screen,
                genre=genre,
                aspect_ratio=aspect_ratio,
                output_filename=f"job_{job_id}_scene_{idx}.jpg"
            )

            # Render Scene Video Clip
            scene_clip = job_temp / f"clip_{idx}.mp4"
            await self._render_scene_clip(
                image_path=image_path,
                audio_path=audio_path,
                duration=scene_duration,
                camera_motion=motion,
                aspect_ratio=aspect_ratio,
                output_path=scene_clip
            )
            clip_paths.append(scene_clip)

            # Track timing for subtitles
            sc_info = dict(sc)
            sc_info["start_time_sec"] = cumulative_time
            sc_info["end_time_sec"] = cumulative_time + scene_duration
            sc_info["duration_sec"] = scene_duration
            cumulative_time += scene_duration
            enriched_scenes.append(sc_info)

        # 2. Concatenate scene clips
        concat_list_file = job_temp / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for cp in clip_paths:
                f.write(f"file '{cp.resolve()}'\n")

        raw_assembled_video = job_temp / "assembled_raw.mp4"
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(raw_assembled_video)
        ]
        proc = await asyncio.create_subprocess_exec(*concat_cmd)
        await proc.communicate()

        final_output_path = self.output_dir / f"CineShorts_{job_id}_{aspect_ratio.replace(':', 'x')}.mp4"

        # 3. Generate and burn subtitles
        if burn_subtitles:
            ass_path = subtitle_engine.generate_ass_subtitles(
                scenes_data=enriched_scenes,
                style=subtitle_style,
                aspect_ratio=aspect_ratio,
                output_filename=f"subtitles_{job_id}.ass"
            )

            burn_cmd = [
                "ffmpeg", "-y",
                "-i", str(raw_assembled_video),
                "-vf", f"ass={ass_path.resolve()}",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-c:a", "copy",
                str(final_output_path)
            ]
            burn_proc = await asyncio.create_subprocess_exec(
                *burn_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await burn_proc.communicate()
            if burn_proc.returncode != 0:
                logger.warning(f"Subtitle burn returned error: {stderr.decode()[:200]}. Using raw assembled video.")
                import shutil
                shutil.copyfile(raw_assembled_video, final_output_path)
        else:
            import shutil
            shutil.copyfile(raw_assembled_video, final_output_path)

        logger.info(f"Video generation completed successfully! -> {final_output_path}")
        return final_output_path

video_engine = VideoEngine()
