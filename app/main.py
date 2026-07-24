"""Aplicacion principal FastAPI."""
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

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CRI Metrics System",
    description="Sistema de KPIs para la Medicion del Riesgo de Ajuste en IA",
    version="1.0.0",
)

app.include_router(api_v1_router)

# Servir archivos estaticos (dashboard)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.on_event("startup")
async def startup_event():
    logging.info("CRI Metrics System iniciado - Dashboard en /static/index.html")
