"""FastAPI entrypoint and REST API for CineShorts AI — Production Grade."""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings, PROJECT_ROOT, WORKSPACE_ROOT
from app.schemas.hook import HookRequest, HookResponse, HookCandidate, HookEvaluation
from app.schemas.research import ResearchRequest, ResearchBrief, ResearchStatusResponse
from app.schemas.script import Script, ScriptGenerationRequest
from app.schemas.video import RenderRequest, RenderResponse, RenderJobStatus, SubtitleStyle, VideoAspect
from app.graph.workflows import create_hook_verification_graph, create_full_production_graph
from app.services import research_service
from app.services.video_engine import video_engine
from app.services.llm_factory import llm_service
from app.services.image_service import image_service
from app.services.tts_service import tts_service
from app.services.ai_video_service import ai_video_service

# Default voices list (edge-tts compatible)
AVAILABLE_VOICES = [
    {"id": "en-US-ChristopherNeural", "label": "Christopher (US)", "lang": "en-US", "gender": "Male"},
    {"id": "en-US-GuyNeural", "label": "Guy (US)", "lang": "en-US", "gender": "Male"},
    {"id": "en-US-JennyNeural", "label": "Jenny (US)", "lang": "en-US", "gender": "Female"},
    {"id": "en-GB-RyanNeural", "label": "Ryan (UK)", "lang": "en-GB", "gender": "Male"},
    {"id": "en-AU-WilliamNeural", "label": "William (AU)", "lang": "en-AU", "gender": "Male"},
]

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agentic AI Video Production Studio: From Viral Shorts to Generative Movies."
)

# CORS middleware for Next.js / Vite frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs folder to serve generated MP4 videos
app.mount("/outputs", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="outputs")

# In-memory jobs tracking
JOBS: Dict[str, Dict[str, Any]] = {}


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": llm_service.provider,
        "llm_model": llm_service.model,
        "image_provider": image_service.active_provider,
        "tts_provider": tts_service.active_provider,
        "status": "ready"
    }


@app.get("/api/providers")
def get_providers():
    """Return which AI providers are active vs using free fallback."""
    return {
        "llm": {
            "provider": llm_service.provider,
            "model": llm_service.model,
            "is_paid": llm_service.provider in ("gemini", "openai", "anthropic"),
        },
        "image": {
            "provider": image_service.active_provider,
            "is_paid": image_service.active_provider in ("gemini3", "imagen", "replicate"),
        },
        "tts": {
            "provider": tts_service.active_provider,
            "is_paid": tts_service.active_provider in ("gemini-tts", "elevenlabs"),
        },
        "research": {
            "deep_research_enabled": settings.DEEP_RESEARCH_ENABLED,
            "can_use_grounded": bool(settings.GEMINI_API_KEY),
        },
        "config": {
            "edit_style": settings.EDIT_STYLE,
            "image_quality": settings.IMAGE_QUALITY,
            "images_per_scene": settings.IMAGES_PER_SCENE,
            "music_enabled": settings.MUSIC_ENABLED,
        }
    }


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "..." + key[-2:]
    return key[:4] + "..." + key[-4:]


class SettingsKeysRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    deep_research_enabled: Optional[bool] = None


@app.get("/api/settings/keys")
def get_settings_keys():
    """Return configured status of API keys (masked for privacy)."""
    return {
        "gemini_api_key_masked": _mask_key(settings.GEMINI_API_KEY),
        "has_gemini_api_key": bool(settings.GEMINI_API_KEY),
        "openai_api_key_masked": _mask_key(settings.OPENAI_API_KEY),
        "has_openai_api_key": bool(settings.OPENAI_API_KEY),
        "anthropic_api_key_masked": _mask_key(settings.ANTHROPIC_API_KEY),
        "has_anthropic_api_key": bool(settings.ANTHROPIC_API_KEY),
        "elevenlabs_api_key_masked": _mask_key(settings.ELEVENLABS_API_KEY),
        "has_elevenlabs_api_key": bool(settings.ELEVENLABS_API_KEY),
        "replicate_api_token_masked": _mask_key(settings.REPLICATE_API_TOKEN),
        "has_replicate_api_token": bool(settings.REPLICATE_API_TOKEN),
        "deep_research_enabled": settings.DEEP_RESEARCH_ENABLED,
        "providers": get_providers(),
    }


@app.post("/api/settings/keys")
def save_settings_keys(req: SettingsKeysRequest):
    """Save API keys to backend/.env and hot-reload all AI services."""
    env_file = PROJECT_ROOT / ".env"

    existing_lines: list[str] = []
    if env_file.exists():
        existing_lines = env_file.read_text(encoding="utf-8").splitlines()

    env_dict: dict[str, str] = {}
    for line in existing_lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_dict[k.strip()] = v.strip()

    # Update keys if provided (and not masked placeholder like "AIza...")
    if req.gemini_api_key is not None and not req.gemini_api_key.startswith("..."):
        clean_key = req.gemini_api_key.strip()
        settings.GEMINI_API_KEY = clean_key
        env_dict["GEMINI_API_KEY"] = clean_key

    if req.openai_api_key is not None and not req.openai_api_key.startswith("..."):
        clean_key = req.openai_api_key.strip()
        settings.OPENAI_API_KEY = clean_key
        env_dict["OPENAI_API_KEY"] = clean_key

    if req.anthropic_api_key is not None and not req.anthropic_api_key.startswith("..."):
        clean_key = req.anthropic_api_key.strip()
        settings.ANTHROPIC_API_KEY = clean_key
        env_dict["ANTHROPIC_API_KEY"] = clean_key

    if req.elevenlabs_api_key is not None and not req.elevenlabs_api_key.startswith("..."):
        clean_key = req.elevenlabs_api_key.strip()
        settings.ELEVENLABS_API_KEY = clean_key
        env_dict["ELEVENLABS_API_KEY"] = clean_key

    if req.replicate_api_token is not None and not req.replicate_api_token.startswith("..."):
        clean_key = req.replicate_api_token.strip()
        settings.REPLICATE_API_TOKEN = clean_key
        env_dict["REPLICATE_API_TOKEN"] = clean_key

    if req.deep_research_enabled is not None:
        settings.DEEP_RESEARCH_ENABLED = req.deep_research_enabled
        env_dict["DEEP_RESEARCH_ENABLED"] = str(req.deep_research_enabled).lower()

    # Write back to both PROJECT_ROOT/.env and WORKSPACE_ROOT/.env
    new_env_content = "\n".join(f"{k}={v}" for k, v in sorted(env_dict.items())) + "\n"
    env_file.write_text(new_env_content, encoding="utf-8")
    workspace_env = WORKSPACE_ROOT / ".env"
    try:
        workspace_env.write_text(new_env_content, encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not mirror .env to workspace root: %s", exc)

    # Hot reload services immediately
    llm_service.reload()
    image_service.reload()
    tts_service.reload()
    ai_video_service.reload()

    logger.info(
        "API keys updated. Hot-reloaded services (LLM: %s, Image: %s, TTS: %s)",
        llm_service.provider,
        image_service.active_provider,
        tts_service.active_provider,
    )

    return {
        "success": True,
        "message": "AI keys saved and services hot-reloaded successfully.",
        "providers": get_providers(),
    }


@app.get("/api/presets")
def get_presets():
    """Return all available genres, voices, aspect ratios, subtitle styles, and edit styles."""
    return {
        "genres": [
            {"id": "informative", "label": "Informative & Science", "description": "High-curiosity documentary breakthroughs with dramatic reveals", "color": "#3B82F6"},
            {"id": "mythology", "label": "Mythology & Ancient Legends", "description": "Epic volumetric lighting, ancient secrets, divine reveals", "color": "#F59E0B"},
            {"id": "horror", "label": "Dark Mystery & Horror", "description": "Chiaroscuro shadows, dread, psychological hooks", "color": "#8B5CF6"},
            {"id": "motivational", "label": "Motivational", "description": "Golden hour, uplifting narrative arcs, inspirational pacing", "color": "#10B981"},
            {"id": "thriller", "label": "Thriller & True Crime", "description": "Cold tones, tension-driven pacing, shocking reveals", "color": "#EF4444"},
            {"id": "comedy", "label": "Comedy & Satire", "description": "Punchy pacing, vibrant chaos, exaggerated moments", "color": "#EC4899"},
            {"id": "scientific", "label": "Scientific Deep Dive", "description": "Precision, data-driven, crisp visual clarity", "color": "#06B6D4"},
            {"id": "sci_fi", "label": "Sci-Fi & Cyberpunk", "description": "Neon flares, holographic tech, interstellar stakes", "color": "#6366F1"},
        ],
        "voices": AVAILABLE_VOICES,
        "aspect_ratios": [
            {"id": "9:16", "label": "Portrait (9:16) — Shorts/Reels", "description": "1080x1920 — YouTube Shorts, Instagram Reels, TikTok", "width": 1080, "height": 1920},
            {"id": "16:9", "label": "Landscape (16:9) — YouTube", "description": "1920x1080 — YouTube long-form, cinematic", "width": 1920, "height": 1080},
        ],
        "subtitle_styles": [
            {"id": SubtitleStyle.HORMOZI_BOLD.value, "label": "Hormozi Viral", "description": "Bold white + yellow highlight, massive black stroke"},
            {"id": SubtitleStyle.BEAST_COLOR.value, "label": "MrBeast Pop", "description": "Impact font, high contrast color punches"},
            {"id": SubtitleStyle.MINIMAL_CLEAN.value, "label": "Clean Modern", "description": "Sleek Helvetica with subtle shadow"},
            {"id": SubtitleStyle.CINEMATIC_NOIR.value, "label": "Cinematic Noir", "description": "Gold serif, film-grain elegance"},
        ],
        "edit_styles": [
            {"id": "fast_cuts", "label": "Fast Cuts (Viral)", "description": "8-12 cuts per 30s, 1.5-2.5s per clip — TikTok/Reels native pacing"},
            {"id": "hybrid", "label": "Hybrid", "description": "Fast hook, medium build, cinematic revelation"},
            {"id": "cinematic", "label": "Cinematic", "description": "4-6 scenes, slow zoompan, documentary feel"},
        ],
        "quality_tiers": [
            {"id": "economy", "label": "Economy (Free)", "description": "Pollinations + Edge-TTS + 1 image/scene", "cost_estimate": "$0"},
            {"id": "production", "label": "Production", "description": "Gemini 2.5 Pro + Gemini TTS + 2 images/scene", "cost_estimate": "~$0.50-1.00/video"},
            {"id": "ultra", "label": "Ultra", "description": "Deep Research + Gemini 3 Pro Image + 3 images/scene", "cost_estimate": "~$2-5/video"},
        ],
        "video_engines": ai_video_service.get_available_engines(),
    }


@app.post("/api/hooks/generate-and-verify", response_model=HookResponse)
async def generate_and_verify_hooks(req: HookRequest):
    """Run the LangGraph hook generator and verification loop."""
    logger.info(f"API: Generating & verifying hooks for topic='{req.topic}', genre='{req.genre}'")
    graph = create_hook_verification_graph()

    # Pre-research topic to ensure real factual grounding
    brief = await research_service.research_topic(
        ResearchRequest(topic=req.topic, genre=req.genre, depth="grounded" if settings.GEMINI_API_KEY else "basic")
    )

    state = {
        "topic": req.topic,
        "genre": req.genre,
        "target_audience": req.target_audience,
        "aspect_ratio": req.aspect_ratio,
        "min_pass_score": req.min_pass_score,
        "max_iterations": req.max_iterations,
        "iteration_count": 0,
        "research_brief": brief.model_dump(),
    }

    result = await graph.ainvoke(state)
    winning_hook = result.get("winning_hook")
    winning_evaluation = result.get("winning_evaluation")

    if not winning_hook and result.get("candidates"):
        winning_hook = result["candidates"][0]
        winning_evaluation = (result.get("evaluations") or [{}])[0]

    return HookResponse(
        topic=req.topic,
        genre=req.genre,
        total_iterations=result.get("iteration_count", 1),
        winning_hook=winning_hook,
        winning_evaluation=winning_evaluation,
        all_iterations=result.get("all_iterations", [])
    )


@app.post("/api/scripts/generate", response_model=Script)
async def generate_scene_script(req: ScriptGenerationRequest):
    """Generate a scene-by-scene storyboard script from a topic or selected hook."""
    logger.info(f"API: Generating scene script for topic='{req.topic}'")
    graph = create_full_production_graph()

    # Ground script generation in real research
    brief = await research_service.research_topic(
        ResearchRequest(topic=req.topic, genre=req.genre, depth="grounded" if settings.GEMINI_API_KEY else "basic")
    )

    state = {
        "topic": req.topic,
        "genre": req.genre,
        "aspect_ratio": req.aspect_ratio,
        "target_duration_sec": req.target_duration_sec,
        "edit_style": getattr(req, "edit_style", settings.EDIT_STYLE),
        "min_pass_score": 80,
        "max_iterations": 3,
        "iteration_count": 0,
        "research_brief": brief.model_dump(),
    }

    if req.selected_hook:
        hook_dict = req.selected_hook.model_dump()
        state["winning_hook"] = hook_dict
        state["selected_hook"] = hook_dict
        state["user_selected_hook"] = hook_dict

    result = await graph.ainvoke(state)
    full_script = result.get("full_script")
    if not full_script:
        raise HTTPException(status_code=500, detail="Failed to assemble script from LangGraph workflow.")

    return Script(**full_script)


async def _run_render_job(job_id: str, request: RenderRequest):
    """Background task to run video rendering pipeline."""
    def on_progress(pct: int, stage_name: str, msg: str):
        if job_id in JOBS:
            JOBS[job_id]["progress_percent"] = pct
            JOBS[job_id]["stage"] = stage_name
            JOBS[job_id]["stage_message"] = msg
            try:
                JOBS[job_id]["status"] = RenderJobStatus(stage_name)
            except ValueError:
                pass
            if msg and (not JOBS[job_id]["logs"] or JOBS[job_id]["logs"][-1] != msg):
                JOBS[job_id]["logs"].append(msg)

    try:
        on_progress(10, "generating_voiceover", "Starting neural voice synthesis & scene generation...")
        script_dict = request.script.model_dump()

        output_path = await video_engine.assemble_full_video(
            script_dict=script_dict,
            voice_name=request.voice_name,
            aspect_ratio=request.aspect_ratio.value,
            subtitle_style=request.subtitle_style,
            burn_subtitles=True,
            include_bg_music=request.include_bg_music,
            bg_music_genre=request.bg_music_genre,
            edit_style=script_dict.get("edit_style", settings.EDIT_STYLE),
            video_engine_mode=getattr(request, "video_engine_mode", "fast_motion"),
            progress_callback=on_progress,
        )

        JOBS[job_id]["status"] = RenderJobStatus.COMPLETED
        JOBS[job_id]["progress_percent"] = 100
        JOBS[job_id]["stage"] = "completed"
        JOBS[job_id]["stage_message"] = "Final MP4 render ready for playback and download"
        JOBS[job_id]["file_path"] = str(output_path)
        JOBS[job_id]["video_url"] = f"/outputs/{output_path.name}"
        logger.info("Job %s finished: %s", job_id, output_path.name)
    except Exception as e:
        logger.error("Render job %s failed: %s", job_id, e, exc_info=True)
        JOBS[job_id]["status"] = RenderJobStatus.FAILED
        JOBS[job_id]["stage"] = "failed"
        JOBS[job_id]["stage_message"] = f"Render error: {str(e)}"
        JOBS[job_id]["error_message"] = str(e)
        JOBS[job_id]["logs"].append(f"ERROR: {str(e)}")


# ── Research endpoints ─────────────────────────────────────────────────────────

@app.post("/api/research/start")
async def start_research(req: ResearchRequest):
    """Kick off a background research job and return a job_id."""
    job_id = await research_service.start_research_job(req)
    return {"job_id": job_id, "status": "in_progress"}


@app.get("/api/research/status/{job_id}")
def get_research_status(job_id: str):
    """Poll the status of a research job."""
    status = research_service.get_research_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Research job {job_id} not found")
    return status


@app.post("/api/research/sync", response_model=ResearchBrief)
async def research_sync(req: ResearchRequest):
    """Run research synchronously (blocks until done — use for small topics)."""
    return await research_service.research_topic(req)


@app.post("/api/video/render", response_model=RenderResponse)
async def start_video_render(req: RenderRequest, background_tasks: BackgroundTasks):
    """Trigger asynchronous video rendering."""
    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {
        "job_id": job_id,
        "status": RenderJobStatus.QUEUED,
        "progress_percent": 5,
        "stage": "queued",
        "stage_message": "Job queued in render pipeline...",
        "logs": ["Job initialized and queued"],
        "video_url": None,
        "file_path": None,
        "error_message": None,
        "duration_sec": None
    }

    background_tasks.add_task(_run_render_job, job_id, req)
    return RenderResponse(
        job_id=job_id,
        status=RenderJobStatus.QUEUED,
        progress_percent=5,
        stage="queued",
        stage_message="Job queued in render pipeline...",
        logs=["Job initialized and queued"],
    )


@app.get("/api/video/status/{job_id}", response_model=RenderResponse)
def get_render_status(job_id: str):
    """Check the status of a video rendering job."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return RenderResponse(**JOBS[job_id])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
