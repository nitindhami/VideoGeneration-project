"""Pydantic schemas for Video Rendering and Jobs."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.script import Script


class SubtitleStyle(str, Enum):
    HORMOZI_BOLD = "hormozi_bold"  # Bold yellow/white uppercase with black stroke
    BEAST_COLOR = "beast_color"    # Green & yellow animated bounce
    MINIMAL_CLEAN = "minimal_clean" # Clean modern white with soft drop shadow
    CINEMATIC_NOIR = "cinematic_noir" # Elegant serif italic gold/white


class VideoAspect(str, Enum):
    PORTRAIT_9_16 = "9:16"    # 1080x1920 Shorts, Reels, TikTok
    LANDSCAPE_16_9 = "16:9"   # 1920x1080 YouTube, Cinema


class RenderJobStatus(str, Enum):
    QUEUED = "queued"
    GENERATING_VOICEOVER = "generating_voiceover"
    GENERATING_VISUALS = "generating_visuals"
    COMPOSITING_VIDEO = "compositing_video"
    BURNING_SUBTITLES = "burning_subtitles"
    COMPLETED = "completed"
    FAILED = "failed"


class RenderRequest(BaseModel):
    script: Script
    voice_name: str = Field(default="en-US-ChristopherNeural", description="Voice ID for TTS")
    voice_rate: str = Field(default="+0%", description="Speech speed adjustment e.g. +10%, -5%")
    voice_pitch: str = Field(default="+0Hz", description="Speech pitch adjustment")
    subtitle_style: SubtitleStyle = Field(default=SubtitleStyle.HORMOZI_BOLD)
    aspect_ratio: VideoAspect = Field(default=VideoAspect.PORTRAIT_9_16)
    include_bg_music: bool = Field(default=True)
    bg_music_genre: str = Field(default="epic_cinematic")
    video_engine_mode: str = Field(default="fast_motion", description="fast_motion | gemini_omni | minimax | luma | hybrid")


class RenderResponse(BaseModel):
    job_id: str
    status: RenderJobStatus
    progress_percent: int
    stage: Optional[str] = None
    stage_message: Optional[str] = None
    logs: Optional[List[str]] = Field(default_factory=list)
    video_url: Optional[str] = None
    file_path: Optional[str] = None
    duration_sec: Optional[float] = None
    error_message: Optional[str] = None
