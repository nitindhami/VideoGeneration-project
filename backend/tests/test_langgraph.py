"""Unit test for LangGraph Hook & Script workflows."""

import asyncio
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.workflows import create_hook_verification_graph, create_full_production_graph


async def main():
    print("Testing LangGraph Hook Verification Graph...")
    hook_graph = create_hook_verification_graph()
    
    initial_state = {
        "topic": "Roman Self-Healing Concrete",
        "genre": "informative",
        "target_audience": "Curious TikTok/Reels viewers",
        "aspect_ratio": "9:16",
        "min_pass_score": 80,
        "max_iterations": 3,
        "iteration_count": 0,
    }
    
    result = await hook_graph.ainvoke(initial_state)
    print(f"Iterations run: {result.get('iteration_count')}")
    print(f"Winning Hook ID: {result.get('winning_hook', {}).get('id')}")
    print(f"Winning Hook Text: {result.get('winning_hook', {}).get('text')}")
    print(f"Total Score: {result.get('winning_evaluation', {}).get('total_score')}/100")
    print("Hook verification passed successfully!")
    
    print("\nTesting Full Production Graph (Hook -> Critic -> Script -> Prompts)...")
    full_graph = create_full_production_graph()
    full_result = await full_graph.ainvoke(initial_state)
    
    scenes = full_result.get("scenes", [])
    print(f"Generated {len(scenes)} scenes.")
    for sc in scenes:
        print(f"  Scene {sc['scene_id']}: [{sc['camera_motion']}] {sc['on_screen_text']} -> {sc['voiceover_text'][:50]}...")
    
    assert len(scenes) >= 4, "Should generate at least 4 scenes"
    assert full_result.get("winning_hook") is not None, "Should have a winning hook"
    print("\nAll LangGraph tests passed with flying colors!")


if __name__ == "__main__":
    asyncio.run(main())
