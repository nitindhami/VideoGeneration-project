"""Deep Research Service — Gemini Deep Research Agent + Search Grounding fallback."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from app.config import settings
from app.schemas.research import ResearchBrief, ResearchRequest

logger = logging.getLogger(__name__)

# In-memory job store (replace with Redis for production)
_research_jobs: dict[str, dict] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_research_prompt(topic: str, genre: str) -> str:
    return f"""You are an expert research analyst and investigative journalist.
Research the topic "{topic}" for a compelling {genre} short video (30-60 seconds).

Provide a structured research brief with:
1. 5-8 KEY FACTS: Specific, verifiable facts with exact numbers, dates, names. NO vague generalities.
2. CONTROVERSY ANGLE: The most surprising, counter-intuitive, or shocking angle most people don't know.
3. 5-7 SURPRISING STATS: Jaw-dropping statistics that will make viewers stop scrolling.
4. 5-6 VISUAL OPPORTUNITIES: Specific scene descriptions that are highly visual and cinematic.
5. 2-3 EXPERT QUOTES: Real or illustrative quotes that add authority.
6. NARRATIVE ARC: A powerful story arc — problem → evidence → revelation → payoff that creates emotional resonance.

Rules:
- Every fact must be SPECIFIC (include numbers, dates, proper nouns)
- No filler, no vague descriptions
- Think: what would make someone pause and say "I never knew that"
- Format for a viral audience that values truth + shock value

Return a JSON object matching this exact structure:
{{
  "topic": "{topic}",
  "key_facts": ["fact1 with specific detail", "fact2..."],
  "controversy_angle": "The single most surprising angle",
  "surprising_stats": ["X% of...", "In year YYYY, ..."],
  "visual_opportunities": ["Specific scene: show X doing Y in Z setting", ...],
  "expert_quotes": ["Quote — Source/Title", ...],
  "narrative_arc": "Hook → Build → Evidence → Revelation → CTA structure",
  "sources": [],
  "research_depth": "grounded"
}}"""


def _parse_research_json(raw: str) -> dict:
    """Extract JSON from LLM response which may have markdown fences."""
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    # Find first { to last }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    return json.loads(raw)


# ──────────────────────────────────────────────────────────────────────────────
# Deep Research via Interactions API
# ──────────────────────────────────────────────────────────────────────────────

async def _run_deep_research(topic: str, genre: str) -> ResearchBrief:
    """Run Gemini Deep Research agent (~$1-3, takes 2-5 minutes)."""
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = f"""Research "{topic}" thoroughly for a viral short-form video script.

Find:
- Specific verified facts with exact numbers and dates
- The most surprising or counter-intuitive truth about this topic
- Statistics that would shock most viewers
- Vivid visual scene opportunities (specific, filmic)
- The best narrative arc: problem -> evidence -> revelation -> emotional payoff
- Expert voices or compelling quotes

Format your final output as a JSON object with keys:
key_facts, controversy_angle, surprising_stats, visual_opportunities, expert_quotes, narrative_arc, sources
"""
        interaction = client.interactions.create(
            input=prompt,
            agent=settings.DEEP_RESEARCH_MODEL,
            background=True,
            agent_config={
                "type": "deep-research",
                "thinking_summaries": "auto",
            },
        )

        interaction_id = interaction.interaction.id
        # Poll for completion (max 5 min)
        for _ in range(60):
            await asyncio.sleep(5)
            status = client.interactions.get(interaction_id)
            if status.status == "completed":
                output = status.steps[-1].content[0].text if status.steps else ""
                data = _parse_research_json(output)
                data["research_depth"] = "deep"
                data["topic"] = topic
                return ResearchBrief(**data)
            if status.status == "failed":
                raise RuntimeError("Deep Research task failed")

        raise TimeoutError("Deep Research timed out after 5 minutes")

    except Exception as exc:
        logger.warning("Deep Research failed (%s), falling back to grounded search", exc)
        return await _run_grounded_search(topic, genre)


# ──────────────────────────────────────────────────────────────────────────────
# Grounded Search via generateContent with google_search tool
# ──────────────────────────────────────────────────────────────────────────────

async def _run_grounded_search(topic: str, genre: str) -> ResearchBrief:
    """Use gemini-2.5-pro with Google Search grounding for research."""
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = _build_research_prompt(topic, genre)

        response = client.models.generate_content(
            model=settings.DEFAULT_LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7,
            ),
        )
        data = _parse_research_json(response.text)
        data["research_depth"] = "grounded"
        data["topic"] = topic
        # Extract source URLs from grounding metadata if available
        try:
            chunks = response.candidates[0].grounding_metadata.grounding_chunks
            data["sources"] = [
                c.web.uri for c in chunks if hasattr(c, "web") and c.web.uri
            ][:8]
        except Exception:
            pass
        return ResearchBrief(**data)

    except Exception as exc:
        logger.warning("Grounded search failed (%s), using basic LLM research", exc)
        return await _run_basic_research(topic, genre)


# ──────────────────────────────────────────────────────────────────────────────
# Basic LLM Research (no API key needed for Gemini — uses LangChain fallback)
# ──────────────────────────────────────────────────────────────────────────────

async def _run_basic_research(topic: str, genre: str) -> ResearchBrief:
    """Pure LLM research with no grounding — fast but not fact-checked."""
    prompt = _build_research_prompt(topic, genre)

    try:
        if settings.GEMINI_API_KEY:
            from google import genai  # type: ignore

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model=settings.DEFAULT_LLM_MODEL,
                contents=prompt,
            )
            raw = response.text
        elif settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI  # type: ignore

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            r = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            raw = r.choices[0].message.content or ""
        elif settings.ANTHROPIC_API_KEY:
            from anthropic import AsyncAnthropic  # type: ignore

            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            r = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = r.content[0].text
        else:
            # Absolute fallback: return a minimal stub
            return _build_stub_brief(topic)

        data = _parse_research_json(raw)
        data["research_depth"] = "basic"
        data["topic"] = topic
        return ResearchBrief(**data)

    except Exception as exc:
        logger.error("All research methods failed: %s", exc)
        return _build_stub_brief(topic)


def _build_stub_brief(topic: str) -> ResearchBrief:
    """Absolute fallback when no API is available."""
    return ResearchBrief(
        topic=topic,
        key_facts=[f"The topic '{topic}' is a subject of growing global interest"],
        controversy_angle=f"Most people fundamentally misunderstand {topic}",
        surprising_stats=["Studies suggest 90% of people don't know the real story"],
        visual_opportunities=[f"Close-up shot of key elements related to {topic}"],
        expert_quotes=[f"Experts call {topic} one of the most misunderstood subjects"],
        narrative_arc="Hook with question → Build curiosity → Evidence → Revelation → CTA",
        research_depth="basic",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

async def research_topic(request: ResearchRequest) -> ResearchBrief:
    """Main entry — routes to the best available research method."""
    if request.depth == "deep" and settings.GEMINI_API_KEY:
        return await _run_deep_research(request.topic, request.genre)
    elif request.depth == "grounded" and settings.GEMINI_API_KEY:
        return await _run_grounded_search(request.topic, request.genre)
    else:
        return await _run_basic_research(request.topic, request.genre)


async def start_research_job(request: ResearchRequest) -> str:
    """Kick off a background research job and return a job_id."""
    job_id = str(uuid.uuid4())
    _research_jobs[job_id] = {"status": "in_progress", "progress_pct": 0, "brief": None, "error": None}

    async def _run():
        try:
            brief = await research_topic(request)
            _research_jobs[job_id]["status"] = "completed"
            _research_jobs[job_id]["progress_pct"] = 100
            _research_jobs[job_id]["brief"] = brief.model_dump()
        except Exception as exc:
            _research_jobs[job_id]["status"] = "failed"
            _research_jobs[job_id]["error"] = str(exc)

    asyncio.create_task(_run())
    return job_id


def get_research_status(job_id: str) -> Optional[dict]:
    return _research_jobs.get(job_id)
