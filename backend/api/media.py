"""
Media API endpoints
Handles image and TTS generation
"""
import sys
from pathlib import Path
from typing import List
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# Add parent directory to path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from image_wrapper import generate_images
from tts import generate_tts

router = APIRouter()

# Request/Response models
class GenerateImagesRequest(BaseModel):
    results: List[dict]
    save_dir: str = "./outputs"

class GenerateTTSRequest(BaseModel):
    results: List[dict]
    save_dir: str = "./outputs"

class MediaResponse(BaseModel):
    task_id: str
    status: str
    message: str

# In-memory task storage
media_tasks_db = {}

def run_image_generation(task_id: str, results: list, save_dir: str):
    """Background task for image generation"""
    try:
        media_tasks_db[task_id] = {"status": "running", "progress": 0}
        generate_images(results, save_dir=save_dir)
        media_tasks_db[task_id] = {"status": "completed", "progress": 100}
    except Exception as e:
        media_tasks_db[task_id] = {"status": "failed", "error": str(e)}

def run_tts_generation(task_id: str, results: list, save_dir: str):
    """Background task for TTS generation"""
    try:
        media_tasks_db[task_id] = {"status": "running", "progress": 0}
        generate_tts(results, save_dir=save_dir)
        media_tasks_db[task_id] = {"status": "completed", "progress": 100}
    except Exception as e:
        media_tasks_db[task_id] = {"status": "failed", "error": str(e)}

@router.post("/generate-images", response_model=MediaResponse)
async def generate_images_endpoint(request: GenerateImagesRequest, background_tasks: BackgroundTasks):
    """
    Generate images from summaries
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        run_image_generation,
        task_id,
        request.results,
        request.save_dir
    )
    
    media_tasks_db[task_id] = {"status": "pending", "progress": 0}
    
    return MediaResponse(
        task_id=task_id,
        status="pending",
        message="Image generation queued"
    )

@router.post("/generate-tts", response_model=MediaResponse)
async def generate_tts_endpoint(request: GenerateTTSRequest, background_tasks: BackgroundTasks):
    """
    Generate TTS audio from summaries
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        run_tts_generation,
        task_id,
        request.results,
        request.save_dir
    )
    
    media_tasks_db[task_id] = {"status": "pending", "progress": 0}
    
    return MediaResponse(
        task_id=task_id,
        status="pending",
        message="TTS generation queued"
    )

@router.get("/media/{date}")
async def list_media(date: str):
    """
    List all media files for a specific date
    """
    outputs_dir = ROOT / "outputs"
    
    images = [f"/outputs/{p.name}" for p in outputs_dir.glob("output_*.png")]
    audio = [f"/outputs/{p.name}" for p in outputs_dir.glob("*.mp3")]
    video = [f"/outputs/{p.name}" for p in outputs_dir.glob("*.mp4")]
    
    return {
        "date": date,
        "images": sorted(images),
        "audio": sorted(audio),
        "video": video[0] if video else None
    }
