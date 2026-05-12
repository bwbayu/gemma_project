from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas.job import GenerationJobModel
from app.services.job_service import get_job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=GenerationJobModel)
def get_job(job_id: str):
    """Fetch the current state of a generation job by its ID."""
    return get_job_service(job_id)
