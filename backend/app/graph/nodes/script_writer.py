"""Script Writer Node — Film-level scriptwriting with research grounding and edit style awareness."""

from __future__ import annotations

import json
import logging
import re
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


def _build_grounded_fallback_scenes(
    topic: str,
    genre: str,
    edit_style: str,
    hook_text: str,
    research_brief: Optional[dict],
    target_duration: int = 30,
) -> tuple[dict, list[dict]]:
    """Build narrative fallback scenes tightly grounded in verified research facts (no AI slop)."""
    facts = []
    stats = []
    quotes = []
    visuals = []
    controversy = ""
    if research_brief:
        facts = research_brief.get("key_facts", [])
        stats = research_brief.get("surprising_stats", [])
        quotes = research_brief.get("expert_quotes", [])
        visuals = research_brief.get("visual_opportunities", [])
    if not facts:
        from app.services.research_service import fetch_open_knowledge
        open_data = fetch_open_knowledge(topic)
        if open_data.get("found"):
            facts = open_data.get("key_facts", [])
            stats = open_data.get("surprising_stats", [])
            if not controversy:
                controversy = f"How {open_data.get('title', topic)} quietly transformed lives across continents."

    topic_clean = topic.title()
    num_scenes = max(4, target_duration // (3 if edit_style == "fast_cuts" else 6))
    scene_dur = round(target_duration / num_scenes, 1)

    vo_lines: list[str] = []
    callouts: list[str] = []
    vis_prompts: list[str] = []
    used_fact_indices: set[int] = set()

    def format_fact_for_voiceover(raw_fact: str) -> str:
        text = raw_fact.strip()
        text = re.sub(r"\([^)]*\)", "", text)
        text = re.sub(r"\s+([,.;!?])", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text.lower().startswith("also known as") or text.lower().startswith("and by his followers"):
            text = f"{topic.title()} was {text}"
        if len(text) > 155:
            m = re.search(r"^(.{60,150})[\.,;]\s", text)
            if m:
                text = m.group(1).strip()
            else:
                words = text.split(" ")
                shortened = []
                cur_len = 0
                for w in words:
                    if cur_len + len(w) + 1 > 140:
                        break
                    shortened.append(w)
                    cur_len += len(w) + 1
                dangling = {"a", "an", "the", "to", "in", "at", "with", "and", "or", "of", "for", "by", "from", "on"}
                while shortened and shortened[-1].lower() in dangling:
                    shortened.pop()
                text = " ".join(shortened)
        text = text.strip()
        if not text.endswith((".", "!", "?")):
            text += "."
        return text

    def get_thematic_metadata(fact_text: str, fallback_idx: int) -> tuple[str, str]:
        fl = fact_text.lower()
        if any(w in fl for w in ["died", "hospital", "words", "samadhi", "coma", "convulsing"]):
            return "FINAL MAHASAMADHI", f"Sacred stone shrine glowing softly in candlelight, fragrant orange marigold garlands, volumetric spiritual rays, 8k documentary depth"
        if any(w in fl for w in ["ram dass", "larry brilliant", "steve jobs", "disciples", "followers", "foundation", "seva", "krishna das"]):
            return "GLOBAL SEEKERS", f"Western disciples and spiritual seekers sitting attentively at the feet of an Indian sage wrapped in a blanket, warm 1970s film aesthetic, 8k"
        if any(w in fl for w in ["born", "birth", "village", "childhood", "parents", "married", "fathered"]):
            return "HUMBLE ORIGINS", f"Authentic historical village setting in India, early 1900s, dusty paths, traditional brick homes, soft golden morning light, 8k cinematic realism"
        if any(w in fl for w in ["sadhu", "hermit", "wandered", "journey", "train"]):
            return "WANDERING SADHU", f"A solitary wandering ascetic monk walking barefoot through misty morning fog along an ancient northern Indian road, cinematic 8k"
        if any(w in fl for w in ["kainchi", "ashram", "temple", "vrindavan", "stayed"]):
            return "SACRED SANCTUARY", f"Serene Himalayan mountain ashram in Kainchi Dham, nestled among lush green pines and running mountain river, temple bells, 8k"
        if any(w in fl for w in ["mela", "pilgrims", "thousands", "gathering"]):
            return "SACRED GATHERING", f"Vibrant mountain pilgrimage festival with thousands gathered peacefully, colorful flags, saffron robes, majestic Himalayan peaks, 8k"
        if any(w in fl for w in ["teachings", "love", "serve", "feed", "remember"]):
            return "CORE TEACHINGS", f"Warm communal gathering sharing humble food and wisdom, heartfelt expressions of unconditional love and unity, warm golden glow, 8k"
        
        default_callouts = ["PIVOTAL MOMENT", "SACRED TRUTH", "TIMELESS IMPACT", "ENDURING LEGACY", "LIVING PROOF"]
        return default_callouts[fallback_idx % len(default_callouts)], f"Atmospheric cinematic documentary scene capturing the profound essence of {topic}, dramatic lighting, 8k resolution"

    def get_next_fact() -> Optional[str]:
        for fi, fact in enumerate(facts):
            if fi not in used_fact_indices:
                used_fact_indices.add(fi)
                return format_fact_for_voiceover(fact)
        return None

    # Scene 1: The Hook
    if hook_text:
        vo_lines.append(hook_text)
    elif controversy:
        vo_lines.append(f"The documented history of {topic} is nothing like what you were taught.")
    else:
        vo_lines.append(f"Behind the quiet legend of {topic} lies a truth that reshaped millions of lives.")
    callouts.append("THE UNTOLD STORY")
    vis_prompts.append(
        visuals[0] if visuals else f"Cinematic atmospheric portrait of {topic}, dramatic lighting, 8k documentary depth"
    )

    # Scene 2: The Origins / Early Years
    f2 = get_next_fact()
    if f2:
        vo_lines.append(f2)
        call, vis = get_thematic_metadata(f2, 0)
        callouts.append(call)
        vis_prompts.append(vis)
    else:
        vo_lines.append(f"Archival records reveal an extraordinary journey that began in complete obscurity.")
        callouts.append("THE ORIGINS")
        vis_prompts.append(visuals[1] if len(visuals) > 1 else f"Authentic historical setting for {topic}, warm golden hour, cinematic realism")

    # Scene 3: The Turning Point / Ashram / Milestone
    f3 = get_next_fact()
    if f3:
        vo_lines.append(f3)
        call, vis = get_thematic_metadata(f3, 1)
        callouts.append(call)
        vis_prompts.append(vis)
    elif stats:
        vo_lines.append(f"Documented records show: {stats[0][:110]}")
        callouts.append("THE TURNING POINT")
        vis_prompts.append(visuals[2] if len(visuals) > 2 else f"Sacred majestic environment associated with {topic}, volumetric light rays")
    else:
        vo_lines.append(f"A profound turning point transformed {topic} from a localized presence to a global inspiration.")
        callouts.append("THE TURNING POINT")
        vis_prompts.append(visuals[2] if len(visuals) > 2 else f"Sacred majestic environment associated with {topic}, volumetric light rays")

    # Scene 4: Legacy / Global Impact / Wisdom
    if quotes:
        vo_lines.append(quotes[0][:120])
        callouts.append("TIMELESS WORDS")
        vis_prompts.append(visuals[3] if len(visuals) > 3 else f"Wide cinematic vista celebrating the enduring spiritual and cultural legacy of {topic}")
    else:
        f4 = get_next_fact()
        if f4:
            vo_lines.append(f4)
            call, vis = get_thematic_metadata(f4, 2)
            callouts.append(call)
            vis_prompts.append(vis)
        else:
            vo_lines.append(f"Decades later, the timeless impact of {topic} continues to ripple across cultures worldwide.")
            callouts.append("TIMELESS LEGACY")
            vis_prompts.append(visuals[3] if len(visuals) > 3 else f"Wide cinematic vista celebrating the enduring spiritual and cultural legacy of {topic}")

    # Subsequent Scenes: Pull real facts chronologically
    while len(vo_lines) < num_scenes:
        next_f = get_next_fact()
        if next_f:
            vo_lines.append(next_f)
            call, vis = get_thematic_metadata(next_f, len(used_fact_indices))
            callouts.append(call)
            vis_prompts.append(vis)
        else:
            # Fallback only if facts exhausted
            concluding_beats = [
                ("Their core message remained unwavering: love everyone, serve everyone, and remember truth.", "UNWAVERING TRUTH"),
                ("Today, seekers from across the globe continue to journey to their sacred sanctuaries.", "LIVING LEGACY"),
                ("Their extraordinary life stands as permanent proof that unconditional love transforms the world.", "PERMANENT IMPACT"),
            ]
            c_idx = len(vo_lines) - len(used_fact_indices)
            b_text, b_call = concluding_beats[c_idx % len(concluding_beats)]
            vo_lines.append(b_text)
            callouts.append(b_call)
            vis_prompts.append(f"Grand wide cinematic vista of {topic}, golden hour sunset, tranquil spiritual atmosphere, 8k masterpiece")

    scenes = []
    for i in range(num_scenes):
        scenes.append({
            "scene_id": i + 1,
            "duration_sec": scene_dur,
            "voiceover_text": vo_lines[i] if i < len(vo_lines) else f"The incredible story of {topic}.",
            "visual_prompt": f"{vis_prompts[i]}, 8k resolution, photorealistic, sharp focus, cinematic color grading, no text, no watermarks",
            "on_screen_text": callouts[i] if i < len(callouts) else "KEY MOMENT",
            "visual_hook_type": "Hard Cut" if i % 2 == 0 else "Whip Pan",
            "camera_motion": "zoom_in" if i % 2 == 0 else "pan_right",
            "transition_to_next": "hard_cut",
            "audio_sfx_cue": "deep bass impact" if i == 0 else ("riser" if i == 1 else "heartbeat"),
            "emphasis_words": [w for w in topic.split() if len(w) > 3][:2],
            "sub_clips": [f"Atmospheric visual cut {i+1} for {topic}", f"Cinematic perspective {i+1}"],
            "cut_timing": [round(scene_dur * 0.4, 2), round(scene_dur * 0.8, 2)],
        })

    fallback_data = {
        "title": f"The True Story of {topic_clean}",
        "topic": topic,
        "genre": genre,
        "edit_style": edit_style,
        "aspect_ratio": "9:16",
        "estimated_total_duration": float(target_duration),
        "research_brief_summary": controversy or f"Grounded historical investigation into the life and legacy of {topic}.",
        "call_to_action": f"Share this with someone who needs to hear the story of {topic}",
        "scenes": scenes,
    }
    return fallback_data, scenes


async def generate_script(state: dict) -> dict:
    """LangGraph node: write a film-level script using research and hook."""
    request: Optional[ScriptGenerationRequest] = state.get("script_request")
    hook_raw = (
        state.get("user_selected_hook")
        or state.get("selected_hook")
        or state.get("winning_hook")
        or (state.get("candidates", [{}])[0] if state.get("candidates") else None)
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

    fallback_data, fallback_scenes = _build_grounded_fallback_scenes(
        topic, genre, edit_style, hook_text, research_brief, target_duration
    )

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
