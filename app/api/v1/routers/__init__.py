from .cri import router as cri_router
from .tmi import router as tmi_router
from .sources import router as sources_router
from .simulation import router as simulation_router
from .ai import router as ai_router
from .ingestion import router as ingestion_router
from .health import router as health_router
from .algorithmic import router as algorithmic_router

from fastapi import APIRouter

combined_router = APIRouter(prefix="/api/v1")
combined_router.include_router(cri_router)
combined_router.include_router(tmi_router)
combined_router.include_router(sources_router)
combined_router.include_router(simulation_router)
combined_router.include_router(ai_router)
combined_router.include_router(ingestion_router)
combined_router.include_router(health_router)
combined_router.include_router(algorithmic_router)
