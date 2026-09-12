"""Pydantic schemas for the Hook Generation and Verification Engine."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class HookArchetype(str, Enum):
    CURIOSITY_GAP = "curiosity_gap"
    PATTERN_INTERRUPT = "pattern_interrupt"
    FORBIDDEN_TRUTH = "forbidden_truth"
    HIGH_STAKES = "high_stakes"
    PARADOX = "paradox"
    QUESTION_LOOP = "question_loop"


class HookCandidate(BaseModel):
    id: str = Field(..., description="Unique hook identifier, e.g. hook_1")
    text: str = Field(..., description="The spoken or textual hook")
    archetype: HookArchetype = Field(..., description="The psychological hook framework used")
    visual_concept: str = Field(..., description="First 2-second visual action/metaphor")
    audio_sfx_cue: str = Field(..., description="Opening audio cue (e.g. dramatic whoosh, heartbeat, record scratch)")
    explanation: str = Field(..., description="Why this hook captures psychological attention")


class HookEvaluation(BaseModel):
    hook_id: str
    retention_pull_score: int = Field(..., ge=0, le=30, description="0-30: Hook strength in first 2 seconds")
    curiosity_index_score: int = Field(..., ge=0, le=25, description="0-25: Unanswered question / mental loop")
    visual_potential_score: int = Field(..., ge=0, le=25, description="0-25: Feasibility of eye-catching visual execution")
    clarity_pacing_score: int = Field(..., ge=0, le=20, description="0-20: Rhythmic delivery & lack of fluff")
    total_score: int = Field(..., ge=0, le=100, description="Composite score (0-100)")
    passed: bool = Field(..., description="True if total_score >= 80")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    actionable_critique: str = Field(..., description="Targeted advice for improvement if not passed")


class HookIteration(BaseModel):
    iteration: int
    candidates: List[HookCandidate]
    evaluations: List[HookEvaluation]
    winner_id: Optional[str] = None


class HookRequest(BaseModel):
    topic: str = Field(..., description="Core subject or story premise")
    genre: str = Field(
        default="informative",
        description="Genre/Tone: mythology, informative, funny, dark_mystery, sci_fi, philosophy",
    )
    target_audience: str = Field(default="Social media viewers (18-35)", description="Target demographic")
    aspect_ratio: str = Field(default="9:16", description="'9:16' for Shorts/Reels or '16:9' for Widescreen")
    min_pass_score: int = Field(default=80, ge=50, le=95, description="Verification threshold for critic approval")
    max_iterations: int = Field(default=3, ge=1, le=5, description="Max refinement loops")


class HookResponse(BaseModel):
    topic: str
    genre: str
    total_iterations: int
    winning_hook: HookCandidate
    winning_evaluation: HookEvaluation
    all_iterations: List[HookIteration]
