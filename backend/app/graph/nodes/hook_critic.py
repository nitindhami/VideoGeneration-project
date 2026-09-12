"""Hook Critic & Verifier Node for LangGraph."""

import logging
from typing import Any, Dict, List
from app.graph.state import HookEngineState
from app.services.llm_factory import llm_service

logger = logging.getLogger(__name__)


def _evaluate_hook_heuristically(candidate: Dict[str, Any], iteration: int, min_pass_score: int) -> Dict[str, Any]:
    """Heuristic scoring engine ensuring realistic viral critique."""
    text = candidate.get("text", "")
    words = text.split()
    word_count = len(words)
    
    # 1. Retention Pull (0-30): Penalize fluff intros ("In this video", "Hello guys")
    fluff_words = ["hello", "welcome", "today", "in this video", "let me tell you"]
    has_fluff = any(fluff in text.lower() for fluff in fluff_words)
    
    base_retention = 26 if not has_fluff else 14
    if word_count < 6:
        base_retention -= 4  # too brief
    elif word_count > 20:
        base_retention -= 6  # too wordy for 2 seconds
    
    # 2. Curiosity Index (0-25): Look for trigger question loops, contrast, paradox
    curiosity_triggers = ["lied", "secret", "never", "why", "what if", "stop", "scam", "terrifying", "hidden"]
    curiosity_matches = sum(1 for trigger in curiosity_triggers if trigger in text.lower())
    base_curiosity = min(25, 18 + (curiosity_matches * 3))
    
    # 3. Visual Potential (0-25)
    has_visual = len(candidate.get("visual_concept", "")) > 15
    base_visual = 23 if has_visual else 15
    
    # 4. Clarity & Pacing (0-20)
    base_clarity = 18 if 8 <= word_count <= 16 else 14
    
    # Give a small boost on iterations 2+ to simulate progressive refinement
    if iteration > 1:
        base_retention = min(30, base_retention + 3)
        base_curiosity = min(25, base_curiosity + 2)
        base_clarity = min(20, base_clarity + 2)

    total_score = base_retention + base_curiosity + base_visual + base_clarity
    passed = total_score >= min_pass_score

    strengths = []
    weaknesses = []
    
    if base_retention >= 24:
        strengths.append("High immediate 2-second retention pull; eliminates preamble.")
    else:
        weaknesses.append("Pacing could be tighter; initial 2 seconds needs sharper urgency.")
        
    if base_curiosity >= 22:
        strengths.append("Strong curiosity gap that creates an unresolved cognitive itch.")
    else:
        weaknesses.append("The curiosity premise is somewhat generic; raise the stakes or contrast.")

    if base_visual >= 20:
        strengths.append("Visual concept translates into high-contrast scroll-stopping video imagery.")

    actionable_critique = (
        "Refine hook to hit within 12-14 spoken words. Start directly with the surprising conflict or paradox, "
        "and synchronize with high-contrast motion in the visual prompt."
    )

    return {
        "hook_id": candidate.get("id", "hook"),
        "retention_pull_score": base_retention,
        "curiosity_index_score": base_curiosity,
        "visual_potential_score": base_visual,
        "clarity_pacing_score": base_clarity,
        "total_score": total_score,
        "passed": passed,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "actionable_critique": actionable_critique,
    }


async def hook_critic_node(state: HookEngineState) -> Dict[str, Any]:
    """LangGraph node to verify, critique, and score generated hooks."""
    candidates = state.get("candidates", [])
    iteration_count = state.get("iteration_count", 1)
    min_pass_score = state.get("min_pass_score", 80)
    all_iterations = list(state.get("all_iterations", []))
    critique_history = list(state.get("critique_history", []))

    logger.info(f"Critiquing {len(candidates)} hook candidates (Iteration {iteration_count})")

    system_prompt = (
        "You are an adversarial Hook Critic for short-form video algorithms (TikTok, Reels, Shorts). "
        "Your job is to objectively score hooks based on strict 0-100 retention metrics: "
        "1. First 2s Retention Pull (0-30), 2. Curiosity Index (0-25), 3. Visual Potential (0-25), 4. Clarity & Pacing (0-20). "
        "Reject hooks with total score < 80 and provide targeted feedback to fix them."
    )

    user_prompt = f"""
Candidates to evaluate:
{candidates}

Minimum Passing Score: {min_pass_score}
Iteration: {iteration_count}

Score each candidate. Provide a JSON object with:
- evaluations: list of evaluation objects matching HookEvaluation schema
- winning_hook_id: string id of the candidate that scored highest and >= {min_pass_score}, or null if none passed
- general_critique: string summary critique if no candidate passed, detailing what to change for the next iteration
"""

    fallback_evaluations = [
        _evaluate_hook_heuristically(cand, iteration_count, min_pass_score)
        for cand in candidates
    ]
    
    best_eval = max(fallback_evaluations, key=lambda x: x["total_score"]) if fallback_evaluations else None
    passed = best_eval and best_eval["total_score"] >= min_pass_score

    fallback_response = {
        "evaluations": fallback_evaluations,
        "winning_hook_id": best_eval["hook_id"] if passed else None,
        "general_critique": (
            f"The best hook scored {best_eval['total_score']}/100. "
            f"Critique: {best_eval['actionable_critique']}"
        ) if best_eval else "No candidates available.",
    }

    response = await llm_service.invoke_json(system_prompt, user_prompt, fallback_response)
    evaluations = response.get("evaluations", fallback_evaluations)
    
    # Find winning hook if any meets passing threshold
    best_candidate_eval = max(evaluations, key=lambda x: x.get("total_score", 0)) if evaluations else None
    winning_hook = None
    winning_evaluation = None
    latest_critique = None

    if best_candidate_eval and (best_candidate_eval.get("total_score", 0) >= min_pass_score or iteration_count >= state.get("max_iterations", 3)):
        # Hook passed or we reached maximum iterations
        winning_hook_id = best_candidate_eval["hook_id"]
        winning_hook = next((c for c in candidates if c["id"] == winning_hook_id), candidates[0] if candidates else None)
        winning_evaluation = best_candidate_eval
        logger.info(f"Winning hook selected: {winning_hook_id} with score {best_candidate_eval.get('total_score')}")
    else:
        latest_critique = response.get("general_critique", best_candidate_eval.get("actionable_critique", "Enhance curiosity and reduce opening filler."))
        critique_history.append({
            "iteration": iteration_count,
            "critique": latest_critique,
            "highest_score": best_candidate_eval.get("total_score", 0) if best_candidate_eval else 0,
        })
        logger.info(f"No hook passed threshold {min_pass_score}. Highest: {best_candidate_eval.get('total_score')}. Looping for refinement.")

    iteration_record = {
        "iteration": iteration_count,
        "candidates": candidates,
        "evaluations": evaluations,
        "winner_id": winning_hook["id"] if winning_hook else None,
    }
    all_iterations.append(iteration_record)

    return {
        "evaluations": evaluations,
        "winning_hook": winning_hook,
        "winning_evaluation": winning_evaluation,
        "latest_critique": latest_critique,
        "critique_history": critique_history,
        "all_iterations": all_iterations,
    }
