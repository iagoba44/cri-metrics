"""Aplicacion principal FastAPI."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.database import engine, Base
from app.api.v1 import router as api_v1_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logging.info("CRI Metrics System iniciado - Dashboard en /static/index.html")
    yield
    # Shutdown
    logging.info("CRI Metrics System detenido")

app = FastAPI(
    title="CRI Metrics System",
    description="Sistema de KPIs para la Medicion del Riesgo de Ajuste en IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_v1_router)

# Servir archivos estaticos (dashboard)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")
