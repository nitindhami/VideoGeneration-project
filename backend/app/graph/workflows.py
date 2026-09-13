"""LangGraph workflow assembly for Hook Verification and Video Production."""

import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.graph.state import HookEngineState
from app.graph.nodes.hook_generator import hook_generator_node
from app.graph.nodes.hook_critic import hook_critic_node
from app.graph.nodes.script_writer import script_writer_node
from app.graph.nodes.prompt_optimizer import prompt_optimizer_node

logger = logging.getLogger(__name__)


def route_hook_evaluation(state: HookEngineState) -> Literal["hook_generator", "script_writer", "__end__"]:
    """Conditional router deciding whether to iterate on hooks or proceed to scriptwriting."""
    winning_hook = state.get("winning_hook")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)

    if winning_hook is not None or iteration_count >= max_iterations:
        logger.info(f"Hook approved or max iterations ({iteration_count}/{max_iterations}) reached.")
        # If the caller is only generating hooks, we can finish at END. If full pipeline, go to script_writer.
        return "script_writer"
    
    logger.info(f"Hook not approved. Rerouting to hook_generator (iteration {iteration_count + 1})")
    return "hook_generator"


def route_hook_only_evaluation(state: HookEngineState) -> Literal["hook_generator", "__end__"]:
    """Router for hook-only generation & verification endpoint."""
    winning_hook = state.get("winning_hook")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)

    if winning_hook is not None or iteration_count >= max_iterations:
        return "__end__"
    return "hook_generator"


def create_hook_verification_graph():
    """Graph that only generates, verifies, and iteratively refines hooks."""
    workflow = StateGraph(HookEngineState)
    
    workflow.add_node("hook_generator", hook_generator_node)
    workflow.add_node("hook_critic", hook_critic_node)
    
    workflow.add_edge(START, "hook_generator")
    workflow.add_edge("hook_generator", "hook_critic")
    
    workflow.add_conditional_edges(
        "hook_critic",
        route_hook_only_evaluation,
        {
            "hook_generator": "hook_generator",
            "__end__": END,
        }
    )
    
    return workflow.compile()


def route_start(state: HookEngineState) -> Literal["hook_generator", "script_writer"]:
    """If hook was already provided by user, skip hook generation and proceed directly to script writer."""
    if state.get("winning_hook") or state.get("selected_hook") or state.get("user_selected_hook"):
        return "script_writer"
    return "hook_generator"


def create_full_production_graph():
    """Full end-to-end graph: Hook -> Critic Loop -> Scene Script -> Prompt Optimizer."""
    workflow = StateGraph(HookEngineState)
    
    workflow.add_node("hook_generator", hook_generator_node)
    workflow.add_node("hook_critic", hook_critic_node)
    workflow.add_node("script_writer", script_writer_node)
    workflow.add_node("prompt_optimizer", prompt_optimizer_node)
    
    workflow.add_conditional_edges(
        START,
        route_start,
        {
            "hook_generator": "hook_generator",
            "script_writer": "script_writer",
        }
    )
    workflow.add_edge("hook_generator", "hook_critic")
    
    workflow.add_conditional_edges(
        "hook_critic",
        route_hook_evaluation,
        {
            "hook_generator": "hook_generator",
            "script_writer": "script_writer",
            "__end__": END,
        }
    )
    
    workflow.add_edge("script_writer", "prompt_optimizer")
    workflow.add_edge("prompt_optimizer", END)
    
    return workflow.compile()
