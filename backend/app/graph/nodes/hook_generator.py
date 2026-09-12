"""Hook Generator Node — Film-level viral hook generation with research grounding."""

from __future__ import annotations

import json
import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.schemas.hook import HookCandidate, HookResponse as HookGenerationResponse
from app.services.llm_factory import llm_service

logger = logging.getLogger(__name__)

HOOK_ARCHETYPES = [
    "SHOCKING_STAT",       # Opens with a jaw-dropping number most people don't know
    "PARADOX_REVEAL",      # Contradicts something the audience thinks is true
    "PATTERN_INTERRUPT",   # Violently breaks expected framing (starts mid-action/thought)
    "INSIDER_EXCLUSIVE",   # "What they don't teach you about X..." — secret knowledge frame
    "COUNTDOWN_TENSION",   # "In 60 seconds, you'll never see X the same way again"
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
- Write exactly what would be SPOKEN by the narrator (not a title)
- Include at least ONE specific verifiable detail (number, date, name, place)
- Create COGNITIVE DISSONANCE — make the viewer feel they must keep watching to resolve it
- Rate each hook 1-10 on: Curiosity Gap, Specificity, Shock Factor, Rewatch Value"""


def _build_hook_prompt(topic: str, genre: str, research_brief: Optional[dict] = None) -> str:
    research_context = ""
    if research_brief:
        facts = "\n".join(f"  - {f}" for f in research_brief.get("key_facts", [])[:5])
        stats = "\n".join(f"  - {f}" for f in research_brief.get("surprising_stats", [])[:4])
        controversy = research_brief.get("controversy_angle", "")
        research_context = f"""
VERIFIED RESEARCH (use these SPECIFIC details in the hooks — not generic statements):
KEY FACTS:
{facts}

SURPRISING STATS:
{stats}

CONTROVERSY ANGLE: {controversy}

⚠️ MANDATE: At least 3 of your 5 hooks MUST use a specific number, date, or name from the research above.
"""

    return f"""Topic: "{topic}" | Genre: {genre}
{research_context}

Write EXACTLY 5 viral hooks using these archetypes: {', '.join(HOOK_ARCHETYPES)}

Each hook must:
1. Be 10-18 spoken words maximum
2. Create an immediate curiosity gap
3. Use hard-consonant openings (not "I", "We", "So")
4. Include at least one specific detail (number, name, place, date)
5. Have natural spoken rhythm — read it aloud; it must flow

Return a JSON array ONLY, no markdown:
[
  {{
    "hook_text": "The exact spoken hook",
    "archetype": "ARCHETYPE_NAME",
    "emotion_trigger": "fear|curiosity|outrage|awe|nostalgia|desire",
    "retention_score": 8.5,
    "opening_word": "first word",
    "why_it_works": "one sentence explanation"
  }},
  ...5 total
]"""


def generate_hooks(state: dict) -> dict:
    """LangGraph node: generate viral hooks with research grounding."""
    topic = state.get("topic", "")
    genre = state.get("genre", "informative")
    research_brief = state.get("research_brief", None)

    logger.info("Generating hooks for: %s (provider: %s)", topic, llm_service.provider)

    try:
        llm = llm_service.get_langchain_llm()
        messages = [
            SystemMessage(content=HOOK_SYSTEM_PROMPT),
            HumanMessage(content=_build_hook_prompt(topic, genre, research_brief)),
        ]
        response = llm.invoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)

        # Strip markdown fences
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        hooks_data = json.loads(raw)
        hooks = []
        for i, h in enumerate(hooks_data[:5]):
            hooks.append(HookCandidate(
                hook_id=i + 1,
                hook_text=h.get("hook_text", ""),
                archetype=h.get("archetype", "SHOCKING_STAT"),
                emotion_trigger=h.get("emotion_trigger", "curiosity"),
                retention_score=float(h.get("retention_score", 7.0)),
                opening_word=h.get("opening_word", h.get("hook_text", "").split()[0] if h.get("hook_text") else ""),
                why_it_works=h.get("why_it_works", ""),
            ))

        result = HookGenerationResponse(
            topic=topic,
            genre=genre,
            hooks=hooks,
            recommended_hook=hooks[0] if hooks else None,
        )
        logger.info("Generated %d hooks", len(hooks))
        return {**state, "hook_response": result, "hooks": hooks}

    except Exception as exc:
        logger.error("Hook generation failed: %s", exc)
        # Return a fallback hook so the pipeline doesn't break
        fallback = HookCandidate(
            hook_id=1,
            hook_text=f"The truth about {topic} that nobody is talking about",
            archetype="INSIDER_EXCLUSIVE",
            emotion_trigger="curiosity",
            retention_score=6.0,
            opening_word="The",
            why_it_works="Creates curiosity gap with exclusive framing",
        )
        result = HookGenerationResponse(topic=topic, genre=genre, hooks=[fallback], recommended_hook=fallback)
        return {**state, "hook_response": result, "hooks": [fallback]}

# Alias for LangGraph workflow compatibility
hook_generator_node = generate_hooks
