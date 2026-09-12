"""Visual Prompt Optimizer Node for LangGraph."""

import logging
from typing import Any, Dict, List
from app.graph.state import HookEngineState

logger = logging.getLogger(__name__)

GENRE_STYLE_ENHANCERS = {
    "mythology": "epic cinematic lighting, dramatic volumetric mist, ancient gold and weathered stone textures, glowing mystical runes, heroic composition, 8k resolution, octane render style, photorealistic masterpiece",
    "informative": "clean high-tech documentary cinematography, sharp macro detail, crisp natural lighting, hyper-realistic, shallow depth of field, 8k professional editorial photography",
    "funny": "vibrant saturated color grading, expressive dynamic character posing, wide-angle exaggerated lens, Pixar and modern 3D stylized lighting, clean sharp render",
    "dark_mystery": "dark atmospheric noir aesthetic, deep chiaroscuro shadows, subtle film grain, muted desaturated cold tones, eerie volumetric fog, anamorphic lens flare, 35mm cinematic film still",
    "sci_fi": "futuristic cyberpunk neon aesthetics, holographic displays, anamorphic blue lens flares, sleek carbon fiber and brushed titanium, Unreal Engine 5 render, cinematic 8k",
}


async def prompt_optimizer_node(state: HookEngineState) -> Dict[str, Any]:
    """Enhance and optimize visual prompts for the underlying image/video generative models."""
    scenes = list(state.get("scenes", []))
    genre = state.get("genre", "informative").lower()
    aspect_ratio = state.get("aspect_ratio", "9:16")
    
    enhancement_tag = GENRE_STYLE_ENHANCERS.get(genre, GENRE_STYLE_ENHANCERS["informative"])
    ratio_prompt = "9:16 vertical smartphone format, centered subject framing" if aspect_ratio == "9:16" else "16:9 cinematic widescreen composition"

    optimized_scenes: List[Dict[str, Any]] = []
    for sc in scenes:
        orig_prompt = sc.get("visual_prompt", "")
        # Combine scene specific description with genre style tags and aspect ratio framing
        optimized_prompt = f"{orig_prompt}, {enhancement_tag}, {ratio_prompt}, highly detailed, cinematic masterpiece"
        sc_copy = dict(sc)
        sc_copy["visual_prompt"] = optimized_prompt
        optimized_scenes.append(sc_copy)

    full_script = dict(state.get("full_script", {}))
    full_script["scenes"] = optimized_scenes

    logger.info(f"Optimized visual prompts for {len(optimized_scenes)} scenes in genre '{genre}'")
    return {
        "scenes": optimized_scenes,
        "full_script": full_script,
    }
