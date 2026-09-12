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


async def generate_script(state: dict) -> dict:
    """LangGraph node: write a film-level script using research and hook."""
    request: Optional[ScriptGenerationRequest] = state.get("script_request")
    hook_raw = state.get("winning_hook") or state.get("selected_hook") or (
        state.get("candidates", [{}])[0] if state.get("candidates") else None
    )
    hook_text = ""
    if isinstance(hook_raw, dict):
        hook_text = hook_raw.get("text", hook_raw.get("hook_text", ""))
    elif hasattr(hook_raw, "text"):
        hook_text = hook_raw.text
    elif hasattr(hook_raw, "hook_text"):
        hook_text = hook_raw.hook_text

    topic = state.get("topic") or (request.topic if request else "Viral Story")
    genre = state.get("genre") or (request.genre if request else "informative")
    aspect_ratio = state.get("aspect_ratio") or (request.aspect_ratio if request else "9:16")
    edit_style = state.get("edit_style") or getattr(request, "edit_style", settings.EDIT_STYLE)
    target_duration = state.get("target_duration_sec") or (request.target_duration_sec if request else 30)
    research_brief = state.get("research_brief", None)

    logger.info("Writing %s script for '%s' (edit_style=%s, provider=%s)",
                genre, topic, edit_style, llm_service.provider)

    prompt = _build_script_prompt(
        topic, genre, target_duration, None, edit_style, research_brief
    )
    if hook_text:
        prompt += f"\n\nOPENING HOOK (must be scene 1 voiceover):\n\"{hook_text}\""

    fallback_scenes = [
        {
            "scene_id": 1,
            "duration_sec": 3.5,
            "voiceover_text": hook_text or f"The untold reality of {topic} will leave you stunned.",
            "visual_prompt": f"Dramatic extreme closeup of {topic}, cinematic 8k lighting",
            "on_screen_text": "THE SECRET REVEALED",
            "visual_hook_type": "Hard Cut",
            "camera_motion": "zoom_in",
            "transition_to_next": "hard_cut",
            "audio_sfx_cue": "heavy bass impact",
            "emphasis_words": ["untold", "stunned"],
            "sub_clips": [f"Macro texture of {topic}", f"Atmospheric perspective of {topic}"],
            "cut_timing": [1.2, 2.4]
        },
        {
            "scene_id": 2,
            "duration_sec": 4.0,
            "voiceover_text": f"For centuries, researchers could not explain how {topic} actually functioned.",
            "visual_prompt": f"Historical archive and architectural blueprint of {topic}, moody lighting",
            "on_screen_text": "UNSOLVED MYSTERY",
            "visual_hook_type": "Whip Pan",
            "camera_motion": "pan_left",
            "transition_to_next": "hard_cut",
            "audio_sfx_cue": "riser and camera shutter",
            "emphasis_words": ["centuries", "explain"],
            "sub_clips": [f"Blueprint closeup of {topic}", f"Laboratory microscope view"],
            "cut_timing": [1.5, 3.0]
        },
        {
            "scene_id": 3,
            "duration_sec": 4.0,
            "voiceover_text": f"Then a groundbreaking discovery revealed an astonishing hidden mechanism.",
            "visual_prompt": f"Microscopic view of active self-assembling reaction in {topic}, volumetric light",
            "on_screen_text": "THE BREAKTHROUGH",
            "visual_hook_type": "Zoom Burst",
            "camera_motion": "zoom_out",
            "transition_to_next": "hard_cut",
            "audio_sfx_cue": "deep sub bass drop",
            "emphasis_words": ["discovery", "astonishing"],
            "sub_clips": [f"Glowing particle reaction in {topic}", f"Time-lapse restoration"],
            "cut_timing": [1.4, 2.8]
        },
        {
            "scene_id": 4,
            "duration_sec": 3.5,
            "voiceover_text": f"Today, this ancient formula is reshaping modern engineering forever.",
            "visual_prompt": f"Futuristic megastructure built with modern bio-concrete, sun flare",
            "on_screen_text": "FUTURE OF TECH",
            "visual_hook_type": "Macro Reveal",
            "camera_motion": "tilt_up",
            "transition_to_next": "hard_cut",
            "audio_sfx_cue": "synth swell and chime",
            "emphasis_words": ["modern", "forever"],
            "sub_clips": [f"Futuristic skyline", f"Engineering blueprint overlay"],
            "cut_timing": [1.2, 2.5]
        },
    ]

    fallback_data = {
        "title": f"The Secret of {topic}",
        "topic": topic,
        "genre": genre,
        "edit_style": edit_style,
        "aspect_ratio": aspect_ratio,
        "estimated_total_duration": 15.0,
        "research_brief_summary": f"Explores key breakthrough engineering mechanisms behind {topic}.",
        "call_to_action": "Follow for more unexplained engineering breakthroughs",
        "scenes": fallback_scenes
    }

    try:
        data = await llm_service.invoke_json(SCRIPT_SYSTEM_PROMPT, prompt, fallback_data)
        if not isinstance(data, dict):
            data = fallback_data

        scenes_raw = data.get("scenes", fallback_scenes)
        scenes = []
        t = 0.0
        for s in scenes_raw:
            dur = float(s.get("duration_sec", 3.5))
            scenes.append(Scene(
                scene_id=int(s.get("scene_id", len(scenes) + 1)),
                start_time_sec=t,
                end_time_sec=t + dur,
                duration_sec=dur,
                voiceover_text=s.get("voiceover_text", ""),
                visual_prompt=s.get("visual_prompt", f"Cinematic scene for {topic}"),
                on_screen_text=s.get("on_screen_text", "VIRAL INSIGHT"),
                visual_hook_type=s.get("visual_hook_type", "Hard Cut"),
                camera_motion=s.get("camera_motion", "zoom_in"),
                transition_to_next=s.get("transition_to_next", "hard_cut"),
                audio_sfx_cue=s.get("audio_sfx_cue", "whoosh"),
                emphasis_words=s.get("emphasis_words", []),
                sub_clips=s.get("sub_clips", []),
                cut_timing=s.get("cut_timing", []),
            ))
            t += dur

        hook_obj = None
        if isinstance(hook_raw, dict) and hook_raw.get("text"):
            hook_obj = {
                "id": hook_raw.get("id", "hook_1"),
                "text": hook_raw.get("text", hook_text),
                "archetype": hook_raw.get("archetype", "curiosity_gap"),
                "visual_concept": hook_raw.get("visual_concept", f"Cinematic reveal of {topic}"),
                "audio_sfx_cue": hook_raw.get("audio_sfx_cue", "sub bass drop"),
                "explanation": hook_raw.get("explanation", "Opening viral hook"),
            }
        elif hook_text:
            hook_obj = {
                "id": "hook_1",
                "text": hook_text,
                "archetype": "curiosity_gap",
                "visual_concept": f"Cinematic reveal of {topic}",
                "audio_sfx_cue": "sub bass drop",
                "explanation": "Opening viral hook",
            }

        full_script = {
            "title": data.get("title", f"The Truth About {topic}"),
            "topic": topic,
            "genre": genre,
            "edit_style": edit_style,
            "aspect_ratio": aspect_ratio,
            "selected_hook": hook_obj,
            "estimated_total_duration": t,
            "research_brief_summary": data.get("research_brief_summary", ""),
            "call_to_action": data.get("call_to_action", "Follow for more daily breakthroughs"),
            "scenes": [sc.model_dump() for sc in scenes],
        }

        logger.info("Script generated: %d scenes, %.1fs total", len(scenes), t)
        return {
            **state,
            "scenes": [sc.model_dump() for sc in scenes],
            "full_script": full_script,
        }

    except Exception as exc:
        logger.error("Script generation failed: %s", exc, exc_info=True)
        return {
            **state,
            "scenes": fallback_scenes,
            "full_script": fallback_data,
        }

# Alias for LangGraph workflow compatibility
script_writer_node = generate_script
