"""
News API endpoints
Handles news collection, summarization, and result retrieval
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# Add parent directory to path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import run as pipeline_run

router = APIRouter()

# Request/Response models
class SummarizeRequest(BaseModel):
    date: str = "2025-08-21"
    max_topics: int = 1
    per_topic_docs: int = 1

class SummarizeResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ResultsResponse(BaseModel):
    date: str
    summaries: list
    images: list
    audio: list
    video: Optional[str] = None

# In-memory task storage (in production, use Redis or database)
tasks_db = {}

def run_pipeline_task(task_id: str, date: str, max_topics: int, per_topic_docs: int):
    """Background task to run pipeline"""
    try:
        tasks_db[task_id] = {"status": "running", "progress": 0}
        
        # Run pipeline
        results = pipeline_run(
            date=date,
            max_topics=max_topics,
            per_topic_docs=per_topic_docs,
            save_name=f"summaries_{date}.json"
        )
        
        tasks_db[task_id] = {
            "status": "completed",
            "progress": 100,
            "result": {
                "date": date,
                "articles_count": len(results),
                "summaries_path": f"outputs/summaries_{date}.json"
            }
        }
    except Exception as e:
        tasks_db[task_id] = {
            "status": "failed",
            "progress": 0,
            "error": str(e)
        }

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_news(request: SummarizeRequest, background_tasks: BackgroundTasks):
    """
    Trigger news collection and summarization
    Returns a task ID for status tracking
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    # Add background task
    background_tasks.add_task(
        run_pipeline_task,
        task_id,
        request.date,
        request.max_topics,
        request.per_topic_docs
    )
    
    tasks_db[task_id] = {"status": "pending", "progress": 0}
    
    return SummarizeResponse(
        task_id=task_id,
        status="pending",
        message="Task queued successfully"
    )

@router.get("/results/{date}", response_model=ResultsResponse)
async def get_results(date: str):
    """
    Retrieve saved results for a specific date
    """
    outputs_dir = ROOT / "outputs"
    summaries_file = outputs_dir / f"summaries_{date}.json"
    
    if not summaries_file.exists():
        raise HTTPException(status_code=404, detail=f"No results found for date: {date}")
    
    # Load summaries
    with open(summaries_file, "r", encoding="utf-8") as f:
        summaries = json.load(f)
    
    # Find images
    images = sorted([
        f"/outputs/{p.name}" 
        for p in outputs_dir.glob("output_*.png")
    ])
    
    # Find audio files
    audio = sorted([
        f"/outputs/{p.name}"
        for p in outputs_dir.glob("*.mp3")
    ])
    
    # Find video
    video_files = list(outputs_dir.glob("*.mp4"))
    video = f"/outputs/{video_files[0].name}" if video_files else None
    
    return ResultsResponse(
        date=date,
        summaries=summaries,
        images=images,
        audio=audio,
        video=video
    )
