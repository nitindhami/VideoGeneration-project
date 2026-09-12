"""Script Writer Node — Film-level scriptwriting with research grounding and edit style awareness."""

from __future__ import annotations

import json
import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.schemas.hook import HookCandidate
from app.schemas.script import Scene, Script, ScriptGenerationRequest
from app.services.llm_factory import llm_service

logger = logging.getLogger(__name__)

SCRIPT_SYSTEM_PROMPT = """You are an elite short-form video scriptwriter who has written for viral channels with 10M+ subscribers.
You blend the narrative depth of Kurzgesagt with the fast-paced shock of MrBeast and the authority of a Netflix documentary.

Your scripts follow the VIRAL RETENTION FORMULA:
- Scene 1 (0-3s): THE HOOK — deliver the opening hook immediately, no preamble
- Scene 2-3 (3-10s): TENSION BUILD — introduce the core conflict or mystery with ONE shocking fact
- Scene 4-5 (10-20s): EVIDENCE DROP — specific data points, names, dates — the proof that builds credibility
- Scene 6-7 (20-27s): REVELATION — the counter-intuitive truth, the payoff moment
- Scene 8 (27-30s): CTA LOOP — end with an unresolved question or "follow for part 2" hook

WRITING RULES (non-negotiable):
1. Every voiceover sentence must contain AT LEAST ONE of: a number, a proper noun, a specific location, or a date
2. NO filler words: "basically", "kind of", "you know", "essentially" — every word earns its place
3. Sentence length: 8-12 words per scene (spoken in 2-3 seconds)
4. Use ACTIVE VOICE only — never passive constructions
5. Each scene needs a distinct emotional beat: curiosity → tension → shock → revelation → urgency
6. Visual prompts must be SPECIFIC and CINEMATIC — describe lighting, perspective, subject, atmosphere
7. For FAST_CUTS edit style: scenes should be 1.5-2.5s each, create 8-10+ cuts across 30s
8. For CINEMATIC style: scenes can be 4-6s, more contemplative pacing
9. Sub-clips: for fast_cuts, provide 2-3 visual variation prompts per scene for multi-image cutting"""


def _scenes_for_duration(target_sec: int, edit_style: str) -> int:
    if edit_style == "fast_cuts":
        return max(8, target_sec // 3)   # ~1 scene per 3s for fast cutting
    elif edit_style == "cinematic":
        return max(4, target_sec // 6)   # ~1 scene per 6s for cinematic
    else:  # hybrid
        return max(6, target_sec // 4)


def _build_script_prompt(
    topic: str,
    genre: str,
    target_duration: int,
    hook: Optional[HookCandidate],
    edit_style: str,
    research_brief: Optional[dict] = None,
) -> str:
    num_scenes = _scenes_for_duration(target_duration, edit_style)
    scene_duration = target_duration / num_scenes

    research_context = ""
    if research_brief:
        facts = "\n".join(f"  {i+1}. {f}" for i, f in enumerate(research_brief.get("key_facts", [])[:6]))
        stats = "\n".join(f"  - {s}" for s in research_brief.get("surprising_stats", [])[:4])
        arc = research_brief.get("narrative_arc", "")
        controversy = research_brief.get("controversy_angle", "")
        visuals = "\n".join(f"  - {v}" for v in research_brief.get("visual_opportunities", [])[:4])
        research_context = f"""
═══ VERIFIED RESEARCH (MANDATORY — embed these specific facts into scenes) ═══
NARRATIVE ARC: {arc}
CONTROVERSY ANGLE: {controversy}

KEY FACTS TO USE:
{facts}

SURPRISING STATS:
{stats}

VISUAL OPPORTUNITIES:
{visuals}

⚠️ MANDATE: You MUST incorporate at least 5 of these specific researched facts/stats into voiceover lines.
Do NOT use vague generalities — cite actual details from the research above.
"""

    hook_instruction = ""
    if hook:
        hook_instruction = f"\nOPENING HOOK (use this EXACTLY as Scene 1 voiceover): \"{hook.hook_text}\"\n"

    return f"""Write a {target_duration}-second {genre} short-form video script about: "{topic}"
{hook_instruction}
Edit style: {edit_style.upper()} ({num_scenes} scenes, ~{scene_duration:.1f}s each)
{research_context}

Generate EXACTLY {num_scenes} scenes.

Return ONLY a valid JSON object (no markdown):
{{
  "title": "Compelling clickbait-adjacent title (5-8 words)",
  "topic": "{topic}",
  "genre": "{genre}",
  "edit_style": "{edit_style}",
  "aspect_ratio": "9:16",
  "estimated_total_duration": {target_duration},
  "research_brief_summary": "2-sentence summary of the key research insight used",
  "call_to_action": "Follow for part 2 | Comment X if you knew this | Share this with someone who needs to hear it",
  "scenes": [
    {{
      "scene_id": 1,
      "duration_sec": {scene_duration:.1f},
      "voiceover_text": "Exact spoken words (8-14 words, specific facts, punchy)",
      "visual_prompt": "Cinematic prompt: [subject], [setting], [lighting], [camera angle], [mood]. 8K, photorealistic, sharp focus. NO text, NO watermarks.",
      "on_screen_text": "2-4 WORD CALLOUT ALL CAPS",
      "visual_hook_type": "Hard Cut|Whip Pan|Zoom Burst|Macro Reveal|Contrast Cut",
      "camera_motion": "zoom_in|zoom_out|pan_left|pan_right|whip_pan|dutch_angle",
      "transition_to_next": "hard_cut|whip_pan|flash_cut|cross_dissolve",
      "audio_sfx_cue": "whoosh|bass_drop|riser|impact|heartbeat|silence",
      "emphasis_words": ["word1", "word2"],
      "sub_clips": ["Alt visual prompt 1 for cut", "Alt visual prompt 2 for cut"],
      "cut_timing": [0.8, 1.6]
    }}
  ]
}}"""


def generate_script(state: dict) -> dict:
    """LangGraph node: write a film-level script using research and hook."""
    request: ScriptGenerationRequest = state.get("script_request")
    hook: Optional[HookCandidate] = state.get("selected_hook") or (
        state.get("hooks", [None])[0]
    )
    research_brief = state.get("research_brief", None)

    if not request:
        logger.error("No script_request in state")
        return state

    topic = request.topic
    genre = request.genre
    edit_style = getattr(request, "edit_style", settings.EDIT_STYLE)
    target_duration = request.target_duration_sec

    logger.info("Writing %s script for '%s' (edit_style=%s, provider=%s)",
                genre, topic, edit_style, llm_service.provider)

    try:
        llm = llm_service.get_langchain_llm()
        messages = [
            SystemMessage(content=SCRIPT_SYSTEM_PROMPT),
            HumanMessage(content=_build_script_prompt(
                topic, genre, target_duration, hook, edit_style, research_brief
            )),
        ]
        response = llm.invoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)

        # Strip markdown fences
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data = json.loads(raw)

        # Build Scene objects
        scenes = []
        t = 0.0
        for s in data.get("scenes", []):
            dur = float(s.get("duration_sec", 3.0))
            scenes.append(Scene(
                scene_id=s.get("scene_id", len(scenes) + 1),
                start_time_sec=t,
                end_time_sec=t + dur,
                duration_sec=dur,
                voiceover_text=s.get("voiceover_text", ""),
                visual_prompt=s.get("visual_prompt", ""),
                on_screen_text=s.get("on_screen_text", ""),
                visual_hook_type=s.get("visual_hook_type", "Hard Cut"),
                camera_motion=s.get("camera_motion", "zoom_in"),
                transition_to_next=s.get("transition_to_next", "hard_cut"),
                audio_sfx_cue=s.get("audio_sfx_cue", "whoosh"),
                emphasis_words=s.get("emphasis_words", []),
                sub_clips=s.get("sub_clips", []),
                cut_timing=s.get("cut_timing", []),
            ))
            t += dur

        script = Script(
            title=data.get("title", topic),
            topic=topic,
            genre=genre,
            edit_style=edit_style,
            aspect_ratio=request.aspect_ratio,
            selected_hook=hook or HookCandidate(
                hook_id=0, hook_text=scenes[0].voiceover_text if scenes else topic,
                archetype="BASIC", emotion_trigger="curiosity", retention_score=6.0,
                opening_word="", why_it_works=""
            ),
            scenes=scenes,
            estimated_total_duration=t,
            call_to_action=data.get("call_to_action", "Follow for more"),
            research_brief_summary=data.get("research_brief_summary", ""),
        )

        logger.info("Script: %d scenes, %.1fs total", len(scenes), t)
        return {**state, "script": script}

    except Exception as exc:
        logger.error("Script generation failed: %s", exc)
        return state

# Alias for LangGraph workflow compatibility
script_writer_node = generate_script
