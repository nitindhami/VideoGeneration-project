"""Pydantic schemas for Deep Research Agent output."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ResearchBrief(BaseModel):
    """Structured research output from Gemini Deep Research or grounded search."""

    topic: str = Field(..., description="The researched topic")
    key_facts: List[str] = Field(
        default_factory=list,
        description="Specific citable facts with numbers, dates, or named sources",
    )
    controversy_angle: str = Field(
        default="",
        description="The most surprising or counter-intuitive angle on this topic",
    )
    surprising_stats: List[str] = Field(
        default_factory=list,
        description="Jaw-dropping statistics that challenge assumptions",
    )
    visual_opportunities: List[str] = Field(
        default_factory=list,
        description="Specific scene descriptions that translate into compelling visuals",
    )
    expert_quotes: List[str] = Field(
        default_factory=list,
        description="Expert quotes or illustrative testimonials",
    )
    narrative_arc: str = Field(
        default="",
        description="Suggested story arc: problem -> evidence -> revelation -> payoff",
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Source citations returned by Deep Research",
    )
    research_depth: str = Field(
        default="basic",
        description="'deep' (Deep Research agent) | 'grounded' (Search grounding) | 'basic' (LLM only)",
    )


class ResearchRequest(BaseModel):
    topic: str
    genre: str = "informative"
    depth: str = Field(
        default="grounded",
        description="'deep' | 'grounded' | 'basic'",
    )


class ResearchStatusResponse(BaseModel):
    job_id: str
    status: str  # "in_progress" | "completed" | "failed"
    progress_pct: int = 0
    brief: Optional[ResearchBrief] = None
    error: Optional[str] = None
