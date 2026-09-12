"""Scene-by-Scene Scriptwriter Node for LangGraph."""

import logging
from typing import Any, Dict, List
from app.graph.state import HookEngineState
from app.services.llm_factory import llm_service

logger = logging.getLogger(__name__)


def _generate_fallback_scenes(topic: str, genre: str, hook_text: str, aspect_ratio: str) -> List[Dict[str, Any]]:
    """Generate high-retention structured scenes tailored by genre."""
    ratio_tag = "9:16 vertical smartphone format" if aspect_ratio == "9:16" else "16:9 cinematic widescreen format"
    
    if genre == "mythology":
        return [
            {
                "scene_id": 1,
                "duration_sec": 3.5,
                "voiceover_text": hook_text,
                "visual_hook_type": "Macro time-lapse zoom",
                "visual_prompt": f"Hyper-realistic cinematic close up of ancient temple sanctum with glowing mystical symbols on marble, volumetric smoke, {ratio_tag}, 8k photorealism",
                "on_screen_text": "FORBIDDEN MYTH",
                "audio_sfx_cue": "sub_bass_drop",
                "camera_motion": "zoom_in",
            },
            {
                "scene_id": 2,
                "duration_sec": 4.0,
                "voiceover_text": f"Deep beneath the surface, ancient scribes inscribed secrets about {topic} that were deemed too dangerous for mortals.",
                "visual_hook_type": "Dolly tracking shot",
                "visual_prompt": f"Dramatic cinematic camera tracking along ancient gold-leaf papyrus scrolls and glowing embers in a lost subterranean vault, {ratio_tag}, cinematic lighting",
                "on_screen_text": "TOO DANGEROUS TO SPEAK",
                "audio_sfx_cue": "torch_flicker_and_whisper",
                "camera_motion": "pan_right",
            },
            {
                "scene_id": 3,
                "duration_sec": 4.5,
                "voiceover_text": "When archaeologists recently translated the lost tablet, they realized it described an actual astronomical event with terrifying precision.",
                "visual_hook_type": "Split-contrast reveal",
                "visual_prompt": f"Mythological celestial eclipse with cosmic lightning arcing across star constellations, ancient stone observatory below, {ratio_tag}, hyper-detailed",
                "on_screen_text": "ASTRONOMICAL WARNING",
                "audio_sfx_cue": "cosmic_riser_hit",
                "camera_motion": "zoom_in",
            },
            {
                "scene_id": 4,
                "duration_sec": 4.0,
                "voiceover_text": f"This proves the ancients did not just tell stories; they preserved an eyewitness record of {topic}.",
                "visual_hook_type": "Wide heroic reveal",
                "visual_prompt": f"Heroic silhouette standing before a colossal carved monolith against a fiery sunset sky, atmospheric dust motes, {ratio_tag}, unreal engine 5 render",
                "on_screen_text": "THEY WERE WITNESSES",
                "audio_sfx_cue": "deep_cinematic_horn",
                "camera_motion": "zoom_out",
            },
            {
                "scene_id": 5,
                "duration_sec": 4.0,
                "voiceover_text": "Which ancient myth do you think holds a real secret? Drop your thoughts below and subscribe for more lost histories.",
                "visual_hook_type": "Closing kinetic loop",
                "visual_prompt": f"Mysterious glowing ancient artifact slowly rotating in mid-air surrounded by golden sparks, dark cinematic studio backdrop, {ratio_tag}",
                "on_screen_text": "WHAT SECRET IS NEXT?",
                "audio_sfx_cue": "heartbeat_fadeout",
                "camera_motion": "zoom_in",
            },
        ]
    else:  # informative, science, funny, etc.
        return [
            {
                "scene_id": 1,
                "duration_sec": 3.5,
                "voiceover_text": hook_text,
                "visual_hook_type": "Rapid pattern interrupt",
                "visual_prompt": f"Extreme high-speed macro shot focusing on {topic}, glowing neon energy ripples, sharp depth of field, {ratio_tag}, award winning 8k photography",
                "on_screen_text": "WAIT FOR THIS",
                "audio_sfx_cue": "whoosh_impact",
                "camera_motion": "zoom_in",
            },
            {
                "scene_id": 2,
                "duration_sec": 4.0,
                "voiceover_text": f"For decades, the standard explanation was completely different, until researchers tested what actually happens beneath the surface.",
                "visual_hook_type": "Dolly zoom transition",
                "visual_prompt": f"Futuristic high-tech research lab with holographic data displays analyzing molecular structure of {topic}, clean modern lighting, {ratio_tag}",
                "on_screen_text": "THE HIDDEN MECHANISM",
                "audio_sfx_cue": "digital_scanner_beep",
                "camera_motion": "pan_left",
            },
            {
                "scene_id": 3,
                "duration_sec": 4.5,
                "voiceover_text": f"It turns out that {topic} creates a chain reaction that completely alters the outcome in less than half a second.",
                "visual_hook_type": "Time-dilation slow motion",
                "visual_prompt": f"Ultra slow-motion explosion of energetic particles colliding and reassembling in mid-air, luminescent amber and cyan hues, {ratio_tag}",
                "on_screen_text": "INSTANT REACTION!",
                "audio_sfx_cue": "sub_bass_drop",
                "camera_motion": "zoom_in",
            },
            {
                "scene_id": 4,
                "duration_sec": 4.0,
                "voiceover_text": "Engineers are now copying this exact biological principle to build next-generation technology.",
                "visual_hook_type": "Dynamic futuristic tilt",
                "visual_prompt": f"Sleek aerospace prototype glowing with cybernetic circuits inspired by {topic}, cinematic studio rim light, {ratio_tag}",
                "on_screen_text": "FUTURE TECH UNLOCKED",
                "audio_sfx_cue": "power_up_synth",
                "camera_motion": "tilt_up",
            },
            {
                "scene_id": 5,
                "duration_sec": 4.0,
                "voiceover_text": "Did you know this before today? Follow to discover the wildest science breakthroughs first.",
                "visual_hook_type": "Visual retention loop",
                "visual_prompt": f"Luminescent hourglass reversing gravity with glowing blue sand flowing upwards, dark cinematic backdrop, {ratio_tag}",
                "on_screen_text": "FOLLOW FOR DAILY DISCOVERIES",
                "audio_sfx_cue": "kinetic_pop",
                "camera_motion": "zoom_out",
            },
        ]


async def script_writer_node(state: HookEngineState) -> Dict[str, Any]:
    """LangGraph node to convert the winning hook into a micro-scene storyboard script."""
    topic = state.get("topic", "Roman Concrete")
    genre = state.get("genre", "informative")
    aspect_ratio = state.get("aspect_ratio", "9:16")
    winning_hook = state.get("winning_hook", {})
    hook_text = winning_hook.get("text", f"This fact about {topic} will blow your mind.")

    logger.info(f"Writing script for topic='{topic}', genre='{genre}', aspect_ratio='{aspect_ratio}'")

    system_prompt = (
        "You are an expert Short-Form Video Director & Scriptwriter. You turn viral hooks into "
        "electrifying 30-second video scripts broken down scene-by-scene (3 to 5 seconds per scene). "
        "Every single scene MUST have: voiceover narration, visual generator prompt, on-screen text, "
        "sound effect cue, and camera motion."
    )

    user_prompt = f"""
Topic: {topic}
Genre: {genre}
Winning Hook: {hook_text}
Aspect Ratio: {aspect_ratio}

Create a 5-scene high-retention video script.
Format your output as a JSON object with:
- title: Short punchy title
- call_to_action: Follow/comment retention loop
- scenes: List of 5 scene objects containing:
  * scene_id (int)
  * duration_sec (float between 3.0 and 5.0)
  * voiceover_text (concise narration line)
  * visual_hook_type (e.g. Macro Zoom, Rapid Reveal)
  * visual_prompt (hyper-detailed image generator prompt specifying lighting, angle, and {aspect_ratio} composition)
  * on_screen_text (punchy 2-4 word bold caption)
  * audio_sfx_cue (sound effect name)
  * camera_motion (one of: zoom_in, zoom_out, pan_left, pan_right, tilt_up)
"""

    fallback_scenes = _generate_fallback_scenes(topic, genre, hook_text, aspect_ratio)
    fallback_script = {
        "title": f"The Secret of {topic}",
        "call_to_action": "Follow for more daily discoveries!",
        "scenes": fallback_scenes,
    }

    response = await llm_service.invoke_json(system_prompt, user_prompt, fallback_script)
    scenes = response.get("scenes", fallback_scenes)
    
    # Calculate cumulative timings
    curr_time = 0.0
    for sc in scenes:
        dur = sc.get("duration_sec", 4.0)
        sc["start_time_sec"] = round(curr_time, 2)
        curr_time += dur
        sc["end_time_sec"] = round(curr_time, 2)

    full_script = {
        "title": response.get("title", f"The Truth About {topic}"),
        "topic": topic,
        "genre": genre,
        "aspect_ratio": aspect_ratio,
        "selected_hook": winning_hook,
        "scenes": scenes,
        "estimated_total_duration": round(curr_time, 2),
        "call_to_action": response.get("call_to_action", "Follow for more!"),
    }

    return {
        "scenes": scenes,
        "full_script": full_script,
    }
