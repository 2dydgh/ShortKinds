"""
Task API endpoints
Handles background task status tracking
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter()

# Import task databases from other modules
from backend.api.news import tasks_db
from backend.api.media import media_tasks_db

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    result: Optional[Any] = None
    error: Optional[str] = None

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Check the status of a background task
    """
    # Check in news tasks
    if task_id in tasks_db:
        task_data = tasks_db[task_id]
        return TaskStatusResponse(
            task_id=task_id,
            status=task_data.get("status", "unknown"),
            progress=task_data.get("progress", 0),
            result=task_data.get("result"),
            error=task_data.get("error")
        )
    
    # Check in media tasks
    if task_id in media_tasks_db:
        task_data = media_tasks_db[task_id]
        return TaskStatusResponse(
            task_id=task_id,
            status=task_data.get("status", "unknown"),
            progress=task_data.get("progress", 0),
            result=task_data.get("result"),
            error=task_data.get("error")
        )
    
    raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

@router.get("/tasks")
async def list_all_tasks():
    """
    List all tasks (for debugging)
    """
    return {
        "news_tasks": list(tasks_db.keys()),
        "media_tasks": list(media_tasks_db.keys())
    }
