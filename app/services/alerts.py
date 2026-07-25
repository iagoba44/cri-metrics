"""Servicio de alertas para CRI Metrics.
Envia notificaciones via webhook cuando se cruzan umbrales de riesgo."""
import logging
import requests
from app.config import get_settings

logger = logging.getLogger(__name__)

class AlertService:
    """Gestiona alertas basadas en umbrales de CRI/TMI."""
    
    def __init__(self):
        self.settings = get_settings()
        self.webhook_url = self.settings.ALERT_WEBHOOK_URL
        self.threshold = self.settings.ALERT_THRESHOLD
        self._last_alert_cri = None
        self._last_alert_divergence = None
    
    def check_and_alert(self, cri_score: float, tmi_score: float = None):
        """
        Verifica condiciones de alerta y envia notificaciones.
        Evita spam: solo alerta cuando cruza el umbral por primera vez.
        """
        alerts = []
        
        # Alerta 1: CRI crítico
        if cri_score > self.threshold:
            if self._last_alert_cri is None or cri_score > self._last_alert_cri + 5:
                msg = f"🚨 CRITICAL RISK: CRI at {cri_score:.2f} (threshold: {self.threshold})"
                alerts.append({"type": "critical", "message": msg})
                self._send_webhook(msg)
                self._last_alert_cri = cri_score
                logger.warning(f"[ALERT] {msg}")
        else:
            self._last_alert_cri = None
        
        # Alerta 2: Divergencia CRI vs TMI
        if tmi_score is not None and abs(cri_score - tmi_score) > 40:
            if self._last_alert_divergence is None:
                msg = f"⚠️ DIVERGENCE: CRI={cri_score:.2f} vs TMI={tmi_score:.2f} (diff={abs(cri_score-tmi_score):.1f})"
                alerts.append({"type": "warning", "message": msg})
                self._send_webhook(msg)
                self._last_alert_divergence = True
                logger.warning(f"[ALERT] {msg}")
        else:
            self._last_alert_divergence = None
        
        return alerts
    
    def _send_webhook(self, message: str):
        """Envia mensaje a webhook configurado."""
        if not self.webhook_url:
            logger.info(f"[ALERT-DRYRUN] {message}")
            return
        
        try:
            payload = {
                "text": message,
                "username": "CRI-Metrics-Bot",
                "icon_emoji": ":warning:",
            }
            requests.post(self.webhook_url, json=payload, timeout=10)
            logger.info(f"[ALERT-WEBHOOK] Sent: {message}")
        except Exception as e:
            logger.error(f"[ALERT-WEBHOOK] Failed: {e}")

# Singleton
_alert_service = AlertService()

def get_alert_service() -> AlertService:
    return _alert_service
