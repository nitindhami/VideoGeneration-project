"""Pydantic schemas for Scene-by-Scene Script Generation."""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.hook import HookCandidate


class Scene(BaseModel):
    scene_id: int = Field(..., description="1-indexed sequence order")
    start_time_sec: float = Field(default=0.0)
    end_time_sec: float = Field(default=0.0)
    duration_sec: float = Field(default=4.0, description="Recommended scene length, 1.5-5 seconds")
    voiceover_text: str = Field(..., description="Narration line for this scene")
    visual_hook_type: str = Field(
        default="Cinematic Dolly",
        description="Type of visual engagement (e.g. Macro Zoom, Rapid Reveal, Hard Cut)",
    )
    visual_prompt: str = Field(..., description="Detailed AI image generator prompt with specific cinematography")
    on_screen_text: str = Field(..., description="Punchy, bold keyword overlay (2-4 words, ALL CAPS)")
    audio_sfx_cue: str = Field(default="whoosh", description="Sound effect trigger (whoosh, bass_drop, riser, impact, heartbeat)")
    camera_motion: str = Field(
        default="zoom_in",
        description="Camera movement: zoom_in, zoom_out, pan_left, pan_right, tilt_up, whip_pan, dutch_angle",
    )
    transition_to_next: str = Field(
        default="hard_cut",
        description="Transition type to next scene: hard_cut, whip_pan, flash_cut, cross_dissolve",
    )
    emphasis_words: List[str] = Field(
        default_factory=list,
        description="Words to highlight in subtitles (shown larger + colored)",
    )
    cut_timing: List[float] = Field(
        default_factory=list,
        description="Sub-clip cut points in seconds (for multi-image fast-cut editing)",
    )
    sub_clips: List[str] = Field(
        default_factory=list,
        description="Variation visual prompt descriptions for each sub-cut within the scene",
    )
    # Media paths populated during production
    image_url_or_path: Optional[str] = None
    audio_path: Optional[str] = None


class Script(BaseModel):
    title: str
    topic: str
    genre: str
    aspect_ratio: str = "9:16"
    edit_style: str = Field(default="fast_cuts", description="fast_cuts | cinematic | hybrid")
    selected_hook: HookCandidate
    scenes: List[Scene]
    estimated_total_duration: float
    call_to_action: str = Field(..., description="Final 2-3s retention loop or follow prompt")
    research_brief_summary: str = Field(default="", description="Key facts injected from research agent")


class ScriptGenerationRequest(BaseModel):
    topic: str
    genre: str = "informative"
    aspect_ratio: str = "9:16"
    target_duration_sec: int = Field(default=30, ge=15, le=60)
    edit_style: str = Field(default="fast_cuts", description="fast_cuts | cinematic | hybrid")
    enable_research: bool = Field(default=False, description="Run Deep Research agent before scriptwriting")
    selected_hook: Optional[HookCandidate] = None
