"""FastAPI entrypoint and REST API for CineShorts AI."""

import asyncio
import logging
import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas.hook import HookRequest, HookResponse, HookCandidate, HookEvaluation
from app.schemas.script import Script, ScriptGenerationRequest
from app.schemas.video import RenderRequest, RenderResponse, RenderJobStatus, SubtitleStyle, VideoAspect
from app.graph.workflows import create_hook_verification_graph, create_full_production_graph
from app.services.tts_service import AVAILABLE_VOICES, tts_service
from app.services.video_engine import video_engine
from app.services.llm_factory import llm_service

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
        "status": "ready"
    }


@app.get("/api/presets")
def get_presets():
    """Return all available genres, voices, aspect ratios, and subtitle styles."""
    return {
        "genres": [
            {
                "id": "mythology",
                "label": "Mythology & Ancient Legends",
                "description": "Epic volumetric lighting, ancient secrets, dramatic divine reveals",
                "color": "#F59E0B"
            },
            {
                "id": "informative",
                "label": "Informative & Science",
                "description": "Microscopic details, futuristic laboratory aesthetics, high-curiosity breakthroughs",
                "color": "#3B82F6"
            },
            {
                "id": "funny",
                "label": "Comedy & Satire",
                "description": "Punchy pop pacing, exaggerated expressions, vibrant colorful chaos",
                "color": "#EC4899"
            },
            {
                "id": "dark_mystery",
                "label": "Dark Mystery & Noir",
                "description": "Chiaroscuro shadows, classified documents, eerie psychological hooks",
                "color": "#8B5CF6"
            },
            {
                "id": "sci_fi",
                "label": "Sci-Fi & Cyberpunk",
                "description": "Anamorphic neon flares, holographic tech, interstellar stakes",
                "color": "#10B981"
            }
        ],
        "voices": AVAILABLE_VOICES,
        "aspect_ratios": [
            {
                "id": "9:16",
                "label": "Portrait (9:16)",
                "description": "Optimized for YouTube Shorts, Instagram Reels, TikTok (1080x1920)",
                "width": 1080,
                "height": 1920
            },
            {
                "id": "16:9",
                "label": "Landscape (16:9)",
                "description": "Optimized for YouTube Long-form, Desktop, and Cinematic Movies (1920x1080)",
                "width": 1920,
                "height": 1080
            }
        ],
        "subtitle_styles": [
            {
                "id": SubtitleStyle.HORMOZI_BOLD.value,
                "label": "Hormozi Viral",
                "description": "Bold yellow & white uppercase with heavy black stroke"
            },
            {
                "id": SubtitleStyle.BEAST_COLOR.value,
                "label": "MrBeast Pop",
                "description": "High contrast impact font with vibrant color punches"
            },
            {
                "id": SubtitleStyle.MINIMAL_CLEAN.value,
                "label": "Clean Modern",
                "description": "Sleek sans-serif with subtle dark background"
            }
        ]
    }


@app.post("/api/hooks/generate-and-verify", response_model=HookResponse)
async def generate_and_verify_hooks(req: HookRequest):
    """Run the LangGraph hook generator and verification loop."""
    logger.info(f"API: Generating & verifying hooks for topic='{req.topic}', genre='{req.genre}'")
    graph = create_hook_verification_graph()

    state = {
        "topic": req.topic,
        "genre": req.genre,
        "target_audience": req.target_audience,
        "aspect_ratio": req.aspect_ratio,
        "min_pass_score": req.min_pass_score,
        "max_iterations": req.max_iterations,
        "iteration_count": 0,
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

    state = {
        "topic": req.topic,
        "genre": req.genre,
        "aspect_ratio": req.aspect_ratio,
        "target_duration_sec": req.target_duration_sec,
        "min_pass_score": 80,
        "max_iterations": 3,
        "iteration_count": 0,
    }

    if req.selected_hook:
        state["winning_hook"] = req.selected_hook.model_dump()

    result = await graph.ainvoke(state)
    full_script = result.get("full_script")
    if not full_script:
        raise HTTPException(status_code=500, detail="Failed to assemble script from LangGraph workflow.")

    return Script(**full_script)


async def _run_render_job(job_id: str, request: RenderRequest):
    """Background task to run video rendering pipeline."""
    try:
        JOBS[job_id]["status"] = RenderJobStatus.GENERATING_VOICEOVER
        JOBS[job_id]["progress_percent"] = 20

        # Video Engine handles audio synthesis, images, composition, and subtitles
        script_dict = request.script.model_dump()
        JOBS[job_id]["status"] = RenderJobStatus.GENERATING_VISUALS
        JOBS[job_id]["progress_percent"] = 45

        output_path = await video_engine.assemble_full_video(
            script_dict=script_dict,
            voice_name=request.voice_name,
            aspect_ratio=request.aspect_ratio.value,
            subtitle_style=request.subtitle_style,
            burn_subtitles=True
        )

        JOBS[job_id]["status"] = RenderJobStatus.COMPLETED
        JOBS[job_id]["progress_percent"] = 100
        JOBS[job_id]["file_path"] = str(output_path)
        JOBS[job_id]["video_url"] = f"/outputs/{output_path.name}"
        JOBS[job_id]["duration_sec"] = await tts_service.get_audio_duration(output_path)
        logger.info(f"Job {job_id} finished successfully: {output_path.name}")
    except Exception as e:
        logger.error(f"Render job {job_id} failed: {e}", exc_info=True)
        JOBS[job_id]["status"] = RenderJobStatus.FAILED
        JOBS[job_id]["error_message"] = str(e)


@app.post("/api/video/render", response_model=RenderResponse)
async def start_video_render(req: RenderRequest, background_tasks: BackgroundTasks):
    """Trigger asynchronous video rendering."""
    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {
        "job_id": job_id,
        "status": RenderJobStatus.QUEUED,
        "progress_percent": 5,
        "video_url": None,
        "file_path": None,
        "error_message": None,
        "duration_sec": None
    }

    background_tasks.add_task(_run_render_job, job_id, req)
    return RenderResponse(
        job_id=job_id,
        status=RenderJobStatus.QUEUED,
        progress_percent=5
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
