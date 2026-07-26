"""Generador de recomendaciones de mercado vía Gemini.
Usa el snapshot completo del sistema para generar análisis y recomendaciones accionables."""
import asyncio
import logging
import json
import re
from typing import Optional, Dict
from datetime import datetime, timezone
from app.config import get_settings

logger = logging.getLogger(__name__)

RECOMMENDATION_PROMPT = """Eres un analista senior de infraestructura de Inteligencia Artificial. 
Genera un reporte ejecutivo de mercado con recomendaciones accionables.

DATOS DEL SISTEMA AHORA:
- CRI (Composite Risk Index): {cri_score}/100 — Zona: {cri_zone}
- TMI (Temperature Market Index): {tmi_score}/100 — Zona: {tmi_zone}
- Variación CRI 24h: {cri_delta} puntos
- Modo: {mode}
- Fuentes activas: {active_sources}/{total_sources}

COMPONENTES TMI:
{tmi_components}

NOTICIAS DEL SECTOR (validadas semánticamente):
{news_context}

SENTIMIENTO ESTRUCTURADO:
- Impacto en Capex: {capex_score}/100
- Impacto en Demanda: {demand_score}/100
- Riesgo Regulatorio: {regulatory_score}/100
- Resumen: {sentiment_summary}

INDICADORES TÉCNICOS:
- Z-Score volatilidad: {zscore}
- EMA suavizado: {ema}
- Pesos dinámicos: {decay_weights}

RESPONDE EXACTAMENTE EN ESTE FORMATO JSON (sin markdown, sin texto adicional):
{{
  "market_summary": "<resumen ejecutivo 2-3 oraciones>",
  "risk_assessment": "<evaluación del riesgo actual>",
  "key_drivers": ["<driver 1>", "<driver 2>", "<driver 3>"],
  "recommendations": ["<recomendación 1>", "<recomendación 2>", "<recomendación 3>"],
  "outlook": "<perspectiva a corto plazo 1-2 oraciones>"
}}"""


class GeminiAnalysis:
    """Genera análisis de mercado y recomendaciones usando Gemini."""

    def __init__(self):
        self.api_key = get_settings().GEMINI_API_KEY

    async def generate(self, snapshot: Dict) -> Dict:
        """Genera el reporte completo con recomendaciones."""
        if not self.api_key:
            return {
                "status": "error",
                "error": "GEMINI_API_KEY no configurada en .env",
                "market_summary": "Configura GEMINI_API_KEY en el archivo .env para activar el análisis por IA.",
            }

        prompt = RECOMMENDATION_PROMPT.format(
            cri_score=snapshot.get("cri_score", "N/A"),
            cri_zone=snapshot.get("cri_zone", "UNKNOWN"),
            tmi_score=snapshot.get("tmi_score", "N/A"),
            tmi_zone=snapshot.get("tmi_zone", "UNKNOWN"),
            cri_delta=snapshot.get("cri_delta_24h", 0),
            mode=snapshot.get("mode", "REAL"),
            active_sources=snapshot.get("active_sources", 0),
            total_sources=snapshot.get("total_sources", 5),
            tmi_components=snapshot.get("tmi_components_text", "No disponible"),
            news_context=snapshot.get("news_context", "No hay noticias recientes."),
            capex_score=snapshot.get("sentiment", {}).get("capex_score", 50),
            demand_score=snapshot.get("sentiment", {}).get("demand_score", 50),
            regulatory_score=snapshot.get("sentiment", {}).get("regulatory_score", 50),
            sentiment_summary=snapshot.get("sentiment", {}).get("summary", "Neutral"),
            zscore=snapshot.get("zscore", "N/A"),
            ema=snapshot.get("ema", "N/A"),
            decay_weights=snapshot.get("decay_text", "N/A"),
        )

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=30,
            )
            text = response.text.strip()
            return self._parse(text)
        except asyncio.TimeoutError:
            logger.error("[GeminiAnalysis] Timeout")
            return {"status": "error", "error": "Gemini no respondió (timeout 30s)"}
        except Exception as e:
            logger.error(f"[GeminiAnalysis] Error: {e}")
            return {"status": "error", "error": str(e)}

    def _parse(self, text: str) -> Dict:
        """Parsea la respuesta JSON de Gemini."""
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(text)
            data["status"] = "success"
            return data
        except json.JSONDecodeError:
            logger.warning(f"[GeminiAnalysis] JSON inválido, extrayendo texto: {text[:100]}")
            return {
                "status": "success",
                "market_summary": text[:300],
                "risk_assessment": "",
                "key_drivers": [],
                "recommendations": [],
                "outlook": "",
            }


_analysis = None

def get_gemini_analysis():
    global _analysis
    if _analysis is None:
        _analysis = GeminiAnalysis()
    return _analysis
