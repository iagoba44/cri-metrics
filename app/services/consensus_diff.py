"""Consensus Diff: Comité de Riesgo Asíncrono.
Toma la telemetría algorítmica (CRI, TMI, noticias validadas)
y la somete a escrutinio de múltiples LLMs gratuitos:
- Gemini 1.5 Flash (vía google-generativeai)
- Llama 3 (vía Groq API)

Calcula el diferencial entre CRI algorítmico y el promedio de los LLMs.
"""
import asyncio
import logging
import json
from typing import Optional, Dict, List
from datetime import datetime, timezone
from app.config import get_settings

logger = logging.getLogger(__name__)

# Prompt estándar para el comité de riesgo
RISK_PROMPT = """Eres un analista de riesgos especializado en infraestructura de Inteligencia Artificial. 
Analiza los siguientes datos de mercado y determina si el riesgo real coincide con la matemática.

DATOS DEL SISTEMA:
- CRI (Composite Risk Index): {cri_score} (0-100, mayor = más riesgo)
- Zona de riesgo: {cri_zone}
- TMI (Temperature Market Index): {tmi_score} (0-100)
- Variación CRI últimas 24h: {cri_delta} puntos
- Modo actual: {mode}

NOTICIAS VALIDADAS (impacto en infraestructura IA):
{news_context}

INSTRUCCIONES:
1. Evalúa si el mercado real coincide o diverge del CRI algorítmico.
2. Si las noticias indican pánico pero el CRI es bajo, el score debe ser alto (divergencia).
3. Si el hardware está caro pero las noticias son positivas, el score puede ser bajo.

RESPONDE EXACTAMENTE EN ESTE FORMATO JSON (sin markdown, sin texto adicional):
{{"ai_risk_score": <entero 0-100>, "reasoning_summary": "<explicación breve en español>"}}"""


class LLMClient:
    """Cliente base para LLMs con timeout y manejo de errores."""

    def __init__(self, name: str, timeout: int = 15):
        self.name = name
        self.timeout = timeout

    async def evaluate(self, prompt: str) -> Optional[Dict]:
        raise NotImplementedError


class GeminiClient(LLMClient):
    """Cliente para Gemini 1.5 Flash (gratuito)."""

    def __init__(self):
        super().__init__("Gemini 2.5 Flash")
        self.api_key = get_settings().GEMINI_API_KEY

    async def evaluate(self, prompt: str) -> Optional[Dict]:
        if not self.api_key:
            logger.warning("[Consensus] GEMINI_API_KEY no configurada")
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=self.timeout,
            )
            text = response.text.strip()
            return self._parse_response(text)
        except asyncio.TimeoutError:
            logger.warning("[Consensus] Gemini timeout")
            return None
        except Exception as e:
            logger.warning(f"[Consensus] Gemini error: {e}", exc_info=True)
            return None

    def _parse_response(self, text: str) -> Optional[Dict]:
        try:
            # Limpiar posibles delimitadores markdown
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"[Consensus] Gemini respuesta no JSON: {text[:100]}")
            return None


class GroqClient(LLMClient):
    """Cliente para Llama 3 vía Groq (gratuito)."""

    def __init__(self):
        super().__init__("Llama 3 (Groq)")
        self.api_key = get_settings().GROQ_API_KEY

    async def evaluate(self, prompt: str) -> Optional[Dict]:
        if not self.api_key:
            logger.warning("[Consensus] GROQ_API_KEY no configurada")
            return None
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=self.api_key)
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=300,
                ),
                timeout=self.timeout,
            )
            text = response.choices[0].message.content.strip()
            return self._parse_response(text)
        except asyncio.TimeoutError:
            logger.warning("[Consensus] Groq timeout")
            return None
        except Exception as e:
            logger.warning(f"[Consensus] Groq error: {e}")
            return None

    def _parse_response(self, text: str) -> Optional[Dict]:
        try:
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"[Consensus] Groq respuesta no JSON: {text[:100]}")
            return None


class FallbackClient(LLMClient):
    """Cliente local fallback: retorna estimación basada en reglas."""

    def __init__(self):
        super().__init__("Fallback (Heurístico)")

    async def evaluate(self, prompt: str) -> Optional[Dict]:
        # Extraer CRI del prompt
        import re
        cri_match = re.search(r"CRI.*?(\d+\.?\d*)", prompt)
        tmi_match = re.search(r"TMI.*?(\d+\.?\d*)", prompt)
        cri = float(cri_match.group(1)) if cri_match else 50.0
        tmi = float(tmi_match.group(1)) if tmi_match else 50.0

        # Regla heurística: si divergencia TMI-CRI > 20, sesgar hacia arriba
        diff = abs(tmi - cri)
        if diff > 20:
            ai_score = min(100, max(0, (cri + tmi) / 2 + diff * 0.3))
            razon = f"Divergencia detectada ({diff:.0f}pts). Score ajustado."
        else:
            ai_score = (cri * 0.6 + tmi * 0.4)
            razon = "Mercado coherente con datos algorítmicos."

        return {
            "ai_risk_score": round(min(100, max(0, ai_score)), 1),
            "reasoning_summary": razon,
        }


class ConsensusDiff:
    """
    Comité de riesgo asíncrono.
    Ejecuta LLMs en paralelo, promedia resultados, calcula diff con CRI.
    """

    def __init__(self):
        self.clients: List[LLMClient] = [
            GeminiClient(),
            GroqClient(),
            FallbackClient(),
        ]

    def build_prompt(self, snapshot: Dict) -> str:
        """Construye el prompt con el snapshot actual del sistema."""
        news = snapshot.get("validated_news", [])
        news_context = "No hay noticias validadas recientes."
        if news:
            lines = []
            for n in news[:10]:
                title = n.get("title", "")
                semantic = n.get("semantic_score", 0)
                lines.append(f"- [{semantic:.2f}] {title}")
            news_context = "\n".join(lines)

        return RISK_PROMPT.format(
            cri_score=snapshot.get("cri_score", "N/A"),
            cri_zone=snapshot.get("cri_zone", "UNKNOWN"),
            tmi_score=snapshot.get("tmi_score", "N/A"),
            cri_delta=snapshot.get("cri_delta_24h", 0),
            mode=snapshot.get("mode", "REAL"),
            news_context=news_context,
        )

    async def run_committee(self, snapshot: Dict) -> Dict:
        """
        Ejecuta todos los LLMs en paralelo y calcula consenso.
        Retorna dict con ai_risk_score, ai_risk_zone, diff, y respuestas individuales.
        """
        prompt = self.build_prompt(snapshot)
        logger.info("[Consensus] Lanzando comité de riesgo...")

        # Ejecutar todos los LLMs en paralelo
        tasks = [client.evaluate(prompt) for client in self.clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filtrar respuestas válidas
        valid_responses = []
        individual = []
        for i, result in enumerate(results):
            client_name = self.clients[i].name
            if isinstance(result, Dict) and "ai_risk_score" in result:
                valid_responses.append(result["ai_risk_score"])
                individual.append({
                    "llm": client_name,
                    "score": result["ai_risk_score"],
                    "reasoning": result.get("reasoning_summary", ""),
                })
                logger.info(f"[Consensus] {client_name}: score={result['ai_risk_score']}")
            else:
                logger.warning(f"[Consensus] {client_name}: sin respuesta válida")
                individual.append({"llm": client_name, "score": None, "reasoning": "Sin respuesta"})

        if not valid_responses:
            logger.error("[Consensus] Ningún LLM respondió. Usando fallback.")
            return {
                "ai_risk_score": None,
                "ai_risk_zone": "UNKNOWN",
                "diff": None,
                "diff_alert": False,
                "cri_algoritmico": snapshot.get("cri_score"),
                "individual": individual,
                "committee_size": 0,
            }

        # Promedio
        avg_score = sum(valid_responses) / len(valid_responses)
        cri_algo = snapshot.get("cri_score")
        diff = abs(avg_score - cri_algo) if cri_algo is not None else None

        # Determinar zona
        if avg_score <= 30:
            zone = "LOW"
        elif avg_score <= 65:
            zone = "MODERATE"
        else:
            zone = "CRITICAL"

        # Alerta por divergencia
        diff_alert = diff is not None and diff > 20

        result = {
            "ai_risk_score": round(avg_score, 2),
            "ai_risk_zone": zone,
            "diff": round(diff, 2) if diff is not None else None,
            "diff_alert": diff_alert,
            "cri_algoritmico": cri_algo,
            "individual": individual,
            "committee_size": len(valid_responses),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if diff_alert:
            logger.warning(f"[Consensus] DIVERGENCIA SEMÁNTICA: diff={diff:.1f}pts")

        logger.info(f"[Consensus] Score={avg_score:.1f} | Diff={diff} | Alert={diff_alert}")
        return result


# Singleton
_consensus = None

def get_consensus_diff() -> ConsensusDiff:
    global _consensus
    if _consensus is None:
        _consensus = ConsensusDiff()
    return _consensus
