"""Sistema de alertas para umbrales críticos."""
import logging
import json
from typing import Dict
from app.models import RiskIndex
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AlertService:
    """Gestiona el despacho de alertas cuando CRI > 65 (CRITICAL)."""

    def send_alert(self, risk_index: RiskIndex, component_details: Dict):
        """Despacha alertas a los consumidores configurados."""
        cri_float = float(risk_index.cri_score)

        # Identificar KPIs detonantes (los que más contribuyen)
        detonantes = sorted(
            component_details.items(),
            key=lambda x: x[1]["normalized_score"] * x[1]["weight"],
            reverse=True,
        )[:2]

        payload = {
            "alert_type": "CRI_CRITICAL",
            "timestamp": risk_index.timestamp.isoformat() if risk_index.timestamp else None,
            "cri_score": cri_float,
            "risk_zone": risk_index.risk_zone,
            "threshold": settings.ALERT_THRESHOLD,
            "detonating_kpis": [
                {
                    "kpi": k,
                    "raw_value": v["raw_value"],
                    "normalized_score": v["normalized_score"],
                    "weight": v["weight"],
                }
                for k, v in detonantes
            ],
            "message": f"ALERTA: Índice CRI en zona CRÍTICA ({cri_float}). KPIs detonantes: {[k for k,_ in detonantes]}",
        }

        # Log de alerta
        logger.critical(json.dumps(payload, ensure_ascii=False))

        # Webhook si está configurado
        if settings.ALERT_WEBHOOK_URL:
            self._send_webhook(payload)

        # Simulación de email
        self._send_email_simulation(payload)

    def _send_webhook(self, payload: Dict):
        """Envía payload a webhook externo."""
        import requests
        try:
            response = requests.post(
                settings.ALERT_WEBHOOK_URL,
                json=payload,
                timeout=10,
            )
            logger.info(f"Webhook response: {response.status_code}")
        except Exception as e:
            logger.error(f"Fallo envío webhook: {e}")

    def _send_email_simulation(self, payload: Dict):
        """Simula envío de email de alerta."""
        logger.info(f"[EMAIL SIMULATION] To: risk-team@company.com | Subject: CRI CRITICAL {payload['cri_score']}")
