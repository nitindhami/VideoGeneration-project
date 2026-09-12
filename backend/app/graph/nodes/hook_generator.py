"""Hook Generator Node for LangGraph."""

import logging
from typing import Any, Dict, List
from app.graph.state import HookEngineState
from app.schemas.hook import HookArchetype
from app.services.llm_factory import llm_service

logger = logging.getLogger(__name__)

GENRE_HOOK_TEMPLATES = {
    "mythology": [
        {
            "archetype": HookArchetype.FORBIDDEN_TRUTH,
            "pattern": "Every history book lied to you about {topic}.",
            "visual_concept": "Ancient golden statue cracking open with dark smoke and glowing eyes.",
            "audio_sfx_cue": "deep_sub_drop_and_thunder",
            "explanation": "Directly confronts established beliefs and creates cognitive dissonance."
        },
        {
            "archetype": HookArchetype.CURIOSITY_GAP,
            "pattern": "Why did ancient priests fear {topic} so much that they banned speaking its name?",
            "visual_concept": "Shadowy temple chamber with torchlight flickering on ancient hieroglyphs.",
            "audio_sfx_cue": "whispering_voices_and_riser",
            "explanation": "Creates an immediate unresolved secret that demands an answer."
        },
        {
            "archetype": HookArchetype.HIGH_STAKES,
            "pattern": "If you looked {topic} in the eyes for 3 seconds, ancient texts say this happened.",
            "visual_concept": "Extreme macro close-up of a mythical deity's glowing iris reflecting thunder.",
            "audio_sfx_cue": "high_tension_heartbeat",
            "explanation": "Puts the viewer in mortal danger through second-person immersion."
        }
    ],
    "informative": [
        {
            "archetype": HookArchetype.PATTERN_INTERRUPT,
            "pattern": "Stop scrolling: your brain is doing something terrifying with {topic} right now.",
            "visual_concept": "Rapid glitch transition zooming into high-speed neural synapses firing.",
            "audio_sfx_cue": "digital_glitch_and_alarm",
            "explanation": "Physically interrupts user scroll with immediate neurological relevance."
        },
        {
            "archetype": HookArchetype.CURIOSITY_GAP,
            "pattern": "Scientists accidentally unlocked {topic}, and what they found makes zero sense.",
            "visual_concept": "Microscope footage revealing impossible geometric crystal movement.",
            "audio_sfx_cue": "cinematic_whoosh_hit",
            "explanation": "Presents an accidental discovery that defies known physics."
        },
        {
            "archetype": HookArchetype.FORBIDDEN_TRUTH,
            "pattern": "The 1% spend millions hiding this fact about {topic}.",
            "visual_concept": "Confidential stamped folder burning away to reveal futuristic blueprints.",
            "audio_sfx_cue": "sub_bass_pulse",
            "explanation": "Taps into hidden knowledge and elitist secret biases."
        }
    ],
    "funny": [
        {
            "archetype": HookArchetype.PATTERN_INTERRUPT,
            "pattern": "I was today years old when I realized {topic} is an absolute scam.",
            "visual_concept": "Freeze-frame record scratch on a comically shocked face with zoom.",
            "audio_sfx_cue": "vinyl_scratch_and_clapping",
            "explanation": "Relatable comedic frustration triggering instant validation."
        },
        {
            "archetype": HookArchetype.PARADOX,
            "pattern": "Whoever invented {topic} was either a pure genius or on 9 cups of espresso.",
            "visual_concept": "Fast split-screen comparing absurd blueprints to real-life chaos.",
            "audio_sfx_cue": "slide_whistle_and_boing",
            "explanation": "Humorous hyperbole that sparks immediate lighthearted intrigue."
        },
        {
            "archetype": HookArchetype.QUESTION_LOOP,
            "pattern": "Tell me why nobody told us {topic} could actually do THIS?",
            "visual_concept": "Quick POV handheld camera pointing in bewilderment at bizarre result.",
            "audio_sfx_cue": "dramatic_cymbal_crash",
            "explanation": "Social conversational tone prompting sharing and comments."
        }
    ],
    "dark_mystery": [
        {
            "archetype": HookArchetype.FORBIDDEN_TRUTH,
            "pattern": "Do not look into {topic} at 3 AM unless you want to lose sleep forever.",
            "visual_concept": "Desaturated security camera timestamp glitching in an empty hallway.",
            "audio_sfx_cue": "creepy_music_box_slowdown",
            "explanation": "Fear-based psychological curiosity; forbidden fruit effect."
        },
        {
            "archetype": HookArchetype.HIGH_STAKES,
            "pattern": "In 1983, a team investigated {topic}. Only one tape was ever recovered.",
            "visual_concept": "VHS tracking lines across degraded footage of an anomalous silhouette.",
            "audio_sfx_cue": "vhs_audio_distortion",
            "explanation": "Found-footage realism triggers intense authentic curiosity."
        },
        {
            "archetype": HookArchetype.CURIOSITY_GAP,
            "pattern": "The government classified everything about {topic} for 75 years. Here is why.",
            "visual_concept": "Black ink redactions sliding off a declassified document in 3D.",
            "audio_sfx_cue": "heavy_metal_door_slam",
            "explanation": "High intrigue surrounding government cover-ups."
        }
    ]
}


async def hook_generator_node(state: HookEngineState) -> Dict[str, Any]:
    """LangGraph node to generate 3 diverse viral hook candidates."""
    topic = state.get("topic", "Self-healing Roman Concrete")
    genre = state.get("genre", "informative").lower()
    iteration_count = state.get("iteration_count", 0) + 1
    critique = state.get("latest_critique")
    
    logger.info(f"Generating hooks: iteration={iteration_count}, genre={genre}, topic={topic}")

    system_prompt = (
        "You are an elite Viral Social Media Strategist who specializes in high-retention hooks "
        "for YouTube Shorts, TikTok, and Instagram Reels. Your hooks maximize viewer watch-time, "
        "ignite instant curiosity in the first 2 seconds, and eliminate any boring intros."
    )

    user_prompt = f"""
Topic: {topic}
Genre: {genre}
Iteration: {iteration_count}
Target Audience: {state.get('target_audience', 'Social media viewers')}

{f'CRITIQUE FROM PREVIOUS ATTEMPT (You MUST address this critique): {critique}' if critique else ''}

Generate 3 distinct, irresistible hook candidates using different viral archetypes:
1. Curiosity Gap
2. Pattern Interrupt
3. Forbidden Truth / High-Stakes Controversy

Format your output as a JSON object with a key 'candidates' containing a list of 3 items with:
- id: "hook_1", "hook_2", "hook_3"
- text: The exact spoken hook (10 to 18 words maximum, punchy and spoken aloud)
- archetype: One of ["curiosity_gap", "pattern_interrupt", "forbidden_truth", "high_stakes", "paradox"]
- visual_concept: Precise visual description of what appears on screen in second 0-2
- audio_sfx_cue: Sound design cue (e.g. sub_bass_drop, whoosh_impact, glitch_alarm)
- explanation: Why this psychologically hooks the brain
"""

    # Heuristic fallback generator if LLM is offline or no key
    templates = GENRE_HOOK_TEMPLATES.get(genre, GENRE_HOOK_TEMPLATES["informative"])
    fallback_candidates: List[Dict[str, Any]] = []
    
    for i, t in enumerate(templates[:3], start=1):
        refined_text = t["pattern"].format(topic=topic)
        if critique and "shorter" in critique.lower():
            refined_text = refined_text.split(",")[0] + "!"
            
        fallback_candidates.append({
            "id": f"hook_{iteration_count}_{i}",
            "text": refined_text,
            "archetype": t["archetype"].value if hasattr(t["archetype"], "value") else str(t["archetype"]),
            "visual_concept": t["visual_concept"],
            "audio_sfx_cue": t["audio_sfx_cue"],
            "explanation": t["explanation"],
        })

    fallback_response = {"candidates": fallback_candidates}

    response = await llm_service.invoke_json(system_prompt, user_prompt, fallback_response)
    candidates = response.get("candidates", fallback_candidates)

    return {
        "iteration_count": iteration_count,
        "candidates": candidates,
    }
