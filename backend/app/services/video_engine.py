"""Video Engine — Multi-cut fast-paced editing with cinematic camera moves and audio mixing.

Edit Styles:
  FAST_CUTS:  8-12 hard cuts per 30s, 1.5-2.5s per clip, viral reel pacing
  CINEMATIC:  4-6 scenes, 4-6s each, slow zoompan + motion blur
  HYBRID:     Fast hook (3 cuts in 5s) -> medium build -> cinematic revelation
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.schemas.script import Script
from app.schemas.video import SubtitleStyle, VideoAspect
from app.services.ai_video_service import ai_video_service
from app.services.audio_mixer import mix_with_music
from app.services.image_service import image_service
from app.services.subtitle_engine import subtitle_engine
from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Camera motion filter builders
# ──────────────────────────────────────────────────────────────────────────────

def _zoompan_filter(camera_motion: str, width: int, height: int, total_frames: int, fps: int = 30) -> str:
    """Build an FFmpeg zoompan filter string for a given camera motion."""
    if camera_motion == "zoom_out":
        z = "max(1.2-0.002*on,1.0)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif camera_motion == "pan_left":
        z = "1.12"
        x = f"min((iw-iw/zoom)*(on/{total_frames}),iw-iw/zoom)"
        y = "ih/2-(ih/zoom/2)"
    elif camera_motion == "pan_right":
        z = "1.12"
        x = f"max((iw-iw/zoom)*(1-on/{total_frames}),0)"
        y = "ih/2-(ih/zoom/2)"
    elif camera_motion == "tilt_up":
        z = "1.1"
        x = "iw/2-(iw/zoom/2)"
        y = f"max((ih-ih/zoom)*(1-on/{total_frames}),0)"
    elif camera_motion == "dutch_angle":
        z = "min(zoom+0.0008,1.15)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif camera_motion == "whip_pan":
        # Fast horizontal blur + pan (simulated with fast pan)
        z = "1.1"
        x = f"(iw-iw/zoom)*(on/{max(total_frames, 1)})"
        y = "ih/2-(ih/zoom/2)"
    else:  # zoom_in (default)
        z = "min(zoom+0.001,1.2)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"

    return (
        f"scale=6000:-1,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={total_frames}:s={width}x{height}:fps={fps},"
        f"format=yuv420p"
    )


def _static_scale_filter(width: int, height: int) -> str:
    """Simple scale + crop filter for hard-cut clips (no motion, ultra fast render)."""
    return f"scale={width*2}:{height*2},crop={width}:{height},format=yuv420p"


# ──────────────────────────────────────────────────────────────────────────────
# FFmpeg helper
# ──────────────────────────────────────────────────────────────────────────────

async def _run_ffmpeg(*args: str, timeout: int = 180) -> tuple[bool, str]:
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + list(args)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        ok = proc.returncode == 0
        return ok, stderr.decode()
    except asyncio.TimeoutError:
        proc.kill()
        return False, "timeout"


async def _get_audio_duration(audio_path: Path) -> float:
    """Use ffprobe to get the duration of an audio file."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
        str(audio_path), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    stdout, _ = await proc.communicate()
    import json
    try:
        data = json.loads(stdout)
        for stream in data.get("streams", []):
            dur = float(stream.get("duration", 0))
            if dur > 0:
                return dur
    except Exception:
        pass
    return 3.0  # Default fallback


# ──────────────────────────────────────────────────────────────────────────────
# Scene clip renderer
# ──────────────────────────────────────────────────────────────────────────────

async def _render_clip(
    image_path: Path,
    audio_path: Path,
    duration: float,
    camera_motion: str,
    width: int,
    height: int,
    output_path: Path,
    fast_cut_mode: bool = False,
) -> Path:
    """Render one image + audio into a video clip."""
    fps = 30
    total_frames = max(int(duration * fps), 1)

    # Fast-cut mode: skip expensive zoompan for sub-2s clips
    if fast_cut_mode and duration < 2.0:
        vf = _static_scale_filter(width, height)
    else:
        vf = _zoompan_filter(camera_motion, width, height, total_frames, fps)

    ok, err = await _run_ffmpeg(
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{duration:.3f}",
        "-pix_fmt", "yuv420p",
        str(output_path),
    )

    if not ok:
        logger.warning("Primary render failed (%s...), trying simple scale", err[:100])
        # Fallback: simple scale, no motion
        vf_fallback = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},format=yuv420p"
        await _run_ffmpeg(
            "-loop", "1",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-vf", vf_fallback,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-t", f"{duration:.3f}",
            str(output_path),
        )

    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Multi-cut scene: assembles 2-3 images into a single fast-cut clip
# ──────────────────────────────────────────────────────────────────────────────

async def _render_multi_cut_scene(
    image_paths: List[Path],
    audio_path: Path,
    total_duration: float,
    width: int,
    height: int,
    output_path: Path,
) -> Path:
    """Assemble multiple images into a single scene clip with hard cuts."""
    if len(image_paths) == 1:
        return await _render_clip(
            image_paths[0], audio_path, total_duration,
            "zoom_in", width, height, output_path
        )

    # Divide duration across sub-clips
    n = len(image_paths)
    motions = ["zoom_in", "pan_left", "zoom_out", "pan_right", "dutch_angle"]
    sub_clips: List[Path] = []

    for i, img_path in enumerate(image_paths):
        sub_dur = total_duration / n
        sub_path = output_path.parent / f"{output_path.stem}_sub{i}.mp4"
        motion = motions[i % len(motions)]

        # Silence sub-clip audio for all but the first (master audio applied separately)
        silent_audio = output_path.parent / f"silence_{i}.aac"
        await _run_ffmpeg(
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono:d={sub_dur:.3f}",
            "-c:a", "aac", "-b:a", "128k",
            str(silent_audio),
        )

        await _render_clip(
            img_path, silent_audio, sub_dur,
            motion, width, height, sub_path, fast_cut_mode=True
        )
        sub_clips.append(sub_path)

    if not sub_clips:
        return await _render_clip(image_paths[0], audio_path, total_duration,
                                   "zoom_in", width, height, output_path)

    # Concat sub-clips, then replace audio with real voiceover
    concat_list = output_path.parent / f"{output_path.stem}_concat_list.txt"
    with open(concat_list, "w") as f:
        for sc in sub_clips:
            f.write(f"file '{sc.resolve()}'\n")

    video_only = output_path.parent / f"{output_path.stem}_noaudio.mp4"
    await _run_ffmpeg(
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", str(video_only)
    )

    # Attach real audio
    await _run_ffmpeg(
        "-i", str(video_only),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_duration:.3f}",
        "-map", "0:v", "-map", "1:a",
        str(output_path),
    )

    # Cleanup
    for sc in sub_clips:
        sc.unlink(missing_ok=True)
    video_only.unlink(missing_ok=True)
    concat_list.unlink(missing_ok=True)

    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Transition effects between scene clips
# ──────────────────────────────────────────────────────────────────────────────

TRANSITION_FILTER = {
    "hard_cut": None,          # No filter — raw concat
    "whip_pan": "zoompan=z=1.0:x='if(gte(on,1),iw,0)':y=0:d=4:s={w}x{h}:fps=30",  # placeholder
    "flash_cut": "fade=t=in:st=0:d=0.07:color=white",
    "cross_dissolve": "fade=t=in:st=0:d=0.2",
}


async def _render_ai_video_clip(
    video_path: Path,
    audio_path: Path,
    target_duration: float,
    width: int,
    height: int,
    output_path: Path,
) -> bool:
    """Scales, crops, and conforms an AI-generated video clip to the scene duration and attaches voiceover."""
    try:
        video_dur = await _get_audio_duration(video_path)
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},format=yuv420p"
        
        args = [
            "-stream_loop", "-1" if video_dur < target_duration - 0.2 else "0",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-t", str(round(target_duration, 2)),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]
        ok, err = await _run_ffmpeg(*args)
        if not ok:
            logger.warning("Conforming AI video clip failed: %s", err[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("Conforming AI video clip error: %s", exc)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────────────────────

class VideoEngine:
    def __init__(self):
        self.output_dir = settings.OUTPUT_DIR
        self.temp_dir = settings.TEMP_DIR / "renders"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def assemble_full_video(
        self,
        script_dict: Dict[str, Any],
        voice_name: str = "",
        aspect_ratio: str = "9:16",
        subtitle_style: SubtitleStyle = SubtitleStyle.HORMOZI_BOLD,
        burn_subtitles: bool = True,
        include_bg_music: bool = True,
        bg_music_genre: str = "",
        edit_style: str = "",
        video_engine_mode: str = "fast_motion",
        progress_callback: Optional[Callable[[int, str, str], None]] = None,
    ) -> Path:
        """Full pipeline: TTS -> Images (multi-cut) -> Scene Clips -> Concat -> Music -> Subtitles -> Final MP4."""
        def report(pct: int, stg: str, msg: str):
            if progress_callback:
                try:
                    progress_callback(pct, stg, msg)
                except Exception as _e:
                    logger.warning("Progress callback error: %s", _e)

        job_id = uuid.uuid4().hex[:8]
        job_temp = self.temp_dir / f"job_{job_id}"
        job_temp.mkdir(parents=True, exist_ok=True)

        scenes = script_dict.get("scenes", [])
        total_scenes = max(len(scenes), 1)
        genre = script_dict.get("genre", "informative")
        _edit_style = edit_style or script_dict.get("edit_style", settings.EDIT_STYLE)
        _voice = voice_name or settings.DEFAULT_VOICE
        music_genre = bg_music_genre or genre

        width = 1080 if aspect_ratio == "9:16" else 1920
        height = 1920 if aspect_ratio == "9:16" else 1080
        fast_cuts = _edit_style == "fast_cuts"

        clip_paths: List[Path] = []
        enriched_scenes: List[Dict[str, Any]] = []
        cumulative_time = 0.0
        all_audio_paths: List[Path] = []

        logger.info("Starting video assembly: %d scenes, edit_style=%s, %s",
                    len(scenes), _edit_style, aspect_ratio)
        report(10, "generating_voiceover", f"Initializing audio & neural voice ({_voice})...")

        # ── Step 1: Generate TTS + images for all scenes ─────────────────────
        for idx, sc in enumerate(scenes, start=1):
            voiceover = sc.get("voiceover_text", "")
            v_prompt = sc.get("visual_prompt", "")
            motion = sc.get("camera_motion", "zoom_in")
            sub_clip_prompts = sc.get("sub_clips", [])

            # Compute progressive percentage between 10% and 65%
            scene_base_pct = 10 + int((idx - 1) / total_scenes * 55)
            report(scene_base_pct, "generating_voiceover", f"[Scene {idx}/{total_scenes}] Synthesizing TTS narration...")

            # Synthesize TTS
            audio_path = await tts_service.synthesize(
                text=voiceover,
                voice_name=_voice,
                output_path=job_temp / f"audio_{idx}.mp3",
            )
            all_audio_paths.append(audio_path)
            actual_duration = await _get_audio_duration(audio_path)

            # Scene duration: slightly padded, capped based on edit style
            if fast_cuts:
                scene_duration = max(actual_duration + 0.1, 1.5)
            else:
                scene_duration = max(actual_duration + 0.3, 3.0)

            # Generate images (multi-cut = 2-3 images, economy = 1)
            use_multi_cut = (fast_cuts and settings.IMAGES_PER_SCENE > 1
                             and image_service.active_provider != "procedural")

            report(scene_base_pct + 3, "generating_visuals", f"[Scene {idx}/{total_scenes}] Generating visual assets ({image_service.active_provider})...")

            if use_multi_cut and sub_clip_prompts:
                image_paths = await image_service.generate_multi_cut_images(
                    primary_prompt=v_prompt,
                    sub_clip_prompts=sub_clip_prompts[:settings.IMAGES_PER_SCENE - 1],
                    genre=genre,
                    aspect=aspect_ratio,
                    output_dir=job_temp,
                )
            else:
                img = await image_service.generate_scene_image(
                    prompt=v_prompt, genre=genre, aspect=aspect_ratio, output_dir=job_temp
                )
                image_paths = [img]

            # Render scene clip (AI Video or 2.5D Motion)
            scene_clip = job_temp / f"clip_{idx:03d}.mp4"
            ai_clip_rendered = False

            # Check if this scene should be generated with true AI Video
            should_use_ai_video = False
            if video_engine_mode in ("gemini_omni", "minimax", "luma"):
                should_use_ai_video = True
            elif video_engine_mode == "hybrid":
                # AI Video on Scene 1 (the critical hook) and middle turning point
                should_use_ai_video = (idx == 1 or idx == max(2, total_scenes // 2))

            if should_use_ai_video:
                report(scene_base_pct + 4, "generating_visuals", f"[Scene {idx}/{total_scenes}] Synthesizing AI Video via {video_engine_mode}...")
                ai_vid_path = await ai_video_service.generate_scene_video(
                    prompt=v_prompt,
                    engine_id=video_engine_mode,
                    first_frame_path=image_paths[0] if image_paths else None,
                    aspect_ratio=aspect_ratio,
                    duration_sec=int(scene_duration),
                    output_dir=job_temp,
                )
                if ai_vid_path and ai_vid_path.exists():
                    conformed = await _render_ai_video_clip(
                        video_path=ai_vid_path,
                        audio_path=audio_path,
                        target_duration=scene_duration,
                        width=width, height=height,
                        output_path=scene_clip,
                    )
                    if conformed and scene_clip.exists():
                        ai_clip_rendered = True
                        report(scene_base_pct + 7, "compositing_video", f"[Scene {idx}/{total_scenes}] AI Video conformed & synchronized!")
                if not ai_clip_rendered:
                    logger.info("Scene %d AI video generation skipped or failed; falling back to 2.5D camera motion", idx)

            if not ai_clip_rendered:
                report(scene_base_pct + 6, "compositing_video", f"[Scene {idx}/{total_scenes}] Rendering camera motion ({motion})...")
                if use_multi_cut and len(image_paths) > 1:
                    await _render_multi_cut_scene(
                        image_paths=image_paths,
                        audio_path=audio_path,
                        total_duration=scene_duration,
                        width=width, height=height,
                        output_path=scene_clip,
                    )
                else:
                    await _render_clip(
                        image_path=image_paths[0],
                        audio_path=audio_path,
                        duration=scene_duration,
                        camera_motion=motion,
                        width=width, height=height,
                        output_path=scene_clip,
                        fast_cut_mode=fast_cuts,
                    )

            clip_paths.append(scene_clip)

            sc_info = dict(sc)
            sc_info.update({
                "start_time_sec": cumulative_time,
                "end_time_sec": cumulative_time + scene_duration,
                "duration_sec": scene_duration,
            })
            enriched_scenes.append(sc_info)
            cumulative_time += scene_duration

        # ── Step 2: Concatenate all clips ─────────────────────────────────────
        report(70, "compositing_video", f"Concatenating {len(clip_paths)} scene clips into master timeline...")
        concat_list_file = job_temp / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for cp in clip_paths:
                if cp.exists():
                    f.write(f"file '{cp.resolve()}'\n")

        raw_video = job_temp / "assembled_raw.mp4"
        ok, err = await _run_ffmpeg(
            "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
            "-c", "copy", str(raw_video)
        )
        if not ok:
            logger.error("Concat failed: %s", err[:200])

        # ── Step 3: Mix background music ─────────────────────────────────────
        mixed_audio_path = job_temp / "mixed_audio.aac"
        if include_bg_music and settings.MUSIC_ENABLED and all_audio_paths:
            report(78, "compositing_video", f"Mixing & ducking dynamic background soundtrack ({music_genre})...")
            # Concat all TTS segments into one audio track first
            concat_audio_list = job_temp / "audio_concat.txt"
            with open(concat_audio_list, "w") as f:
                for ap in all_audio_paths:
                    if ap.exists():
                        f.write(f"file '{ap.resolve()}'\n")
            full_voice = job_temp / "full_voice.aac"
            await _run_ffmpeg(
                "-f", "concat", "-safe", "0", "-i", str(concat_audio_list),
                "-c:a", "aac", "-b:a", "192k", str(full_voice)
            )
            if full_voice.exists():
                mixed_audio = await mix_with_music(
                    voice_path=full_voice,
                    output_path=mixed_audio_path,
                    genre=music_genre,
                    video_duration_sec=cumulative_time,
                )
                # Replace audio in assembled video
                with_music_video = job_temp / "assembled_with_music.mp4"
                await _run_ffmpeg(
                    "-i", str(raw_video),
                    "-i", str(mixed_audio),
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-map", "0:v", "-map", "1:a",
                    "-shortest",
                    str(with_music_video),
                )
                if with_music_video.exists():
                    raw_video = with_music_video

        # ── Step 4: Burn subtitles ────────────────────────────────────────────
        final_path = self.output_dir / f"CineShorts_{job_id}_{aspect_ratio.replace(':', 'x')}.mp4"

        if burn_subtitles:
            report(88, "burning_subtitles", f"Synthesizing and burning dynamic {subtitle_style.value} typography...")
            ass_path = subtitle_engine.generate_ass_subtitles(
                scenes_data=enriched_scenes,
                style=subtitle_style,
                aspect_ratio=aspect_ratio,
                output_filename=f"subs_{job_id}.ass",
            )
            ok, err = await _run_ffmpeg(
                "-i", str(raw_video),
                "-vf", f"ass={ass_path.resolve()}",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-c:a", "copy",
                str(final_path),
            )
            if not ok:
                logger.warning("Subtitle burn failed: %s — using raw", err[:150])
                shutil.copy2(raw_video, final_path)
        else:
            shutil.copy2(raw_video, final_path)

        report(100, "completed", f"Video render completed successfully: {final_path.name}")
        logger.info("Video complete: %s (%.1fs, %d scenes)", final_path.name, cumulative_time, len(scenes))
        return final_path


video_engine = VideoEngine()
