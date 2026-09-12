"""Hook Generator Node — Film-level viral hook generation with research grounding."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.schemas.hook import HookArchetype, HookCandidate, HookResponse as HookGenerationResponse
from app.services.llm_factory import llm_service

logger = logging.getLogger(__name__)

HOOK_ARCHETYPES = [
    "curiosity_gap",       # Opens with a jaw-dropping unanswered question or secret
    "pattern_interrupt",   # Violently breaks expected framing (starts mid-action/shock)
    "forbidden_truth",     # "The truth they don't want you to know about X..."
    "high_stakes",         # High urgency or catastrophic/consequential stakes
    "paradox",             # Contradicts something the audience assumes is true
    "question_loop",       # Unresolved cognitive question that demands an answer
]

HOOK_SYSTEM_PROMPT = """You are the world's most effective viral hook writer for short-form video.
You have studied thousands of the highest-retention YouTube Shorts, TikToks, and Reels.

You understand:
- The human brain decides to keep watching within the FIRST 1.5 SECONDS of audio
- The spoken hook must be 10-18 words maximum
- The opening phoneme must be PUNCHY (hard consonants: "The truth about...", "Nobody told you...", "In 1973, the...")
- Hooks that include SPECIFIC NUMBERS outperform vague hooks 3:1
- Questions perform worse than statements — make declarations
- Rhythm matters: the hook should have natural spoken cadence with a beat drop

For each hook:
- Write exactly what would be SPOKEN by the narrator (text)
- Choose a valid archetype: curiosity_gap, pattern_interrupt, forbidden_truth, high_stakes, paradox, question_loop
- Describe a high-contrast 0-2s visual concept (visual_concept)
- Specify an audio sfx cue (audio_sfx_cue e.g. "heavy bass drop with camera shutter")
- Explain why it captures psychological attention (explanation)"""


def _build_hook_prompt(topic: str, genre: str, research_brief: Optional[dict] = None) -> str:
    research_context = ""
    if research_brief:
        facts = "\n".join(f"  - {f}" for f in research_brief.get("key_facts", [])[:5])
        stats = "\n".join(f"  - {f}" for f in research_brief.get("surprising_stats", [])[:4])
        controversy = research_brief.get("controversy_angle", "")
        research_context = f"""
VERIFIED RESEARCH:
KEY FACTS:
{facts}

SURPRISING STATS:
{stats}

CONTROVERSY ANGLE: {controversy}
"""

    return f"""Topic: "{topic}" | Genre: {genre}
{research_context}

Write EXACTLY 5 viral hooks using these archetypes: curiosity_gap, pattern_interrupt, forbidden_truth, high_stakes, paradox, question_loop.

Return a JSON array ONLY, no markdown:
[
  {{
    "id": "hook_1",
    "text": "The exact spoken hook in 10-18 words",
    "archetype": "curiosity_gap",
    "visual_concept": "Macro zoom on cracked Roman concrete with glowing crystal seals",
    "audio_sfx_cue": "heavy sub bass drop and stone crack",
    "explanation": "Creates immediate cognitive dissonance with verified ancient engineering"
  }}
]"""


async def generate_hooks(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: generate viral hooks with research grounding."""
    topic = state.get("topic", "")
    genre = state.get("genre", "informative")
    research_brief = state.get("research_brief", None)
    iteration_count = state.get("iteration_count", 0) + 1
    latest_critique = state.get("latest_critique")

    logger.info("Generating hooks for: %s (iteration %d, provider: %s)", topic, iteration_count, llm_service.provider)

    prompt = _build_hook_prompt(topic, genre, research_brief)
    if latest_critique:
        prompt += f"\n\nPREVIOUS CRITIQUE TO FIX:\n{latest_critique}"

    try:
        raw_json = await llm_service.invoke_json(
            HOOK_SYSTEM_PROMPT,
            prompt,
            fallback_response=[
                {
                    "id": "hook_1",
                    "text": f"The hidden truth about {topic} that history tried to bury.",
                    "archetype": "forbidden_truth",
                    "visual_concept": f"Dramatic cinematic reveal of {topic} under harsh spotlight",
                    "audio_sfx_cue": "deep bass impact and riser",
                    "explanation": "Taps into curiosity gap and forbidden knowledge framing",
                },
                {
                    "id": "hook_2",
                    "text": f"Why 99% of people completely misunderstand how {topic} actually works.",
                    "archetype": "pattern_interrupt",
                    "visual_concept": f"Fast glitch cut showing unexpected reality of {topic}",
                    "audio_sfx_cue": "record scratch and rapid whoosh",
                    "explanation": "Challenges common beliefs and stops scroll",
                },
                {
                    "id": "hook_3",
                    "text": f"If you think you know {topic}, this one discovery changes everything.",
                    "archetype": "paradox",
                    "visual_concept": f"High contrast split-screen comparison of {topic}",
                    "audio_sfx_cue": "heartbeat tempo buildup",
                    "explanation": "Creates unresolved curiosity loop",
                }
            ]
        )

        candidates_data = raw_json if isinstance(raw_json, list) else raw_json.get("hooks", raw_json.get("candidates", []))
        if not candidates_data and isinstance(raw_json, dict):
            candidates_data = [raw_json]

        valid_archetypes = {a.value for a in HookArchetype}
        candidates: List[Dict[str, Any]] = []

        for i, h in enumerate(candidates_data[:5], start=1):
            arch = str(h.get("archetype", "curiosity_gap")).lower()
            if arch not in valid_archetypes:
                arch = "curiosity_gap"

            cand = {
                "id": str(h.get("id") or f"hook_{i}"),
                "text": str(h.get("text") or h.get("hook_text") or f"The untold story behind {topic}."),
                "archetype": arch,
                "visual_concept": str(h.get("visual_concept") or f"Cinematic visual closeup of {topic}"),
                "audio_sfx_cue": str(h.get("audio_sfx_cue") or "dramatic whoosh and bass hit"),
                "explanation": str(h.get("explanation") or h.get("why_it_works") or "Immediate scroll stopping curiosity"),
            }
            candidates.append(cand)

        if not candidates:
            candidates = [
                {
                    "id": "hook_1",
                    "text": f"The hidden secret of {topic} that changes everything.",
                    "archetype": "forbidden_truth",
                    "visual_concept": f"Cinematic reveal of {topic}",
                    "audio_sfx_cue": "sub bass drop",
                    "explanation": "High retention curiosity trigger",
                }
            ]

        logger.info("Generated %d hook candidates", len(candidates))
        return {
            **state,
            "candidates": candidates,
            "iteration_count": iteration_count,
        }

    except Exception as exc:
        logger.error("Hook generation failed: %s", exc, exc_info=True)
        fallback = [
            {
                "id": "hook_1",
                "text": f"The untold truth about {topic} that nobody talks about.",
                "archetype": "forbidden_truth",
                "visual_concept": f"Dramatic cinematic reveal of {topic}",
                "audio_sfx_cue": "dramatic bass impact",
                "explanation": "Instant curiosity gap",
            }
        ]
        return {
            **state,
            "candidates": fallback,
            "iteration_count": iteration_count,
        }

# Alias for LangGraph workflow compatibility
hook_generator_node = generate_hooks
