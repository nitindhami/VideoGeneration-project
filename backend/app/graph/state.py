"""Graph state definition for the LangGraph video production workflow."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class HookEngineState(TypedDict, total=False):
    # Inputs
    topic: str
    genre: str
    target_audience: str
    aspect_ratio: str
    target_duration_sec: int
    min_pass_score: int
    max_iterations: int
    
    # Execution Tracking
    iteration_count: int
    latest_critique: Optional[str]
    critique_history: List[Dict[str, Any]]
    
    # Candidate Hooks and Evaluations
    candidates: List[Dict[str, Any]]
    evaluations: List[Dict[str, Any]]
    all_iterations: List[Dict[str, Any]]
    
    # Selected Winning Hook
    winning_hook: Optional[Dict[str, Any]]
    winning_evaluation: Optional[Dict[str, Any]]
    
    # Storyboard & Script Output
    scenes: List[Dict[str, Any]]
    full_script: Optional[Dict[str, Any]]
    
    # Final production artifacts
    audio_paths: List[str]
    image_paths: List[str]
    video_output_path: Optional[str]
