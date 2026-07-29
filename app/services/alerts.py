"""Servicio de alertas para CRI Metrics.
Envia notificaciones via webhook y correo cuando se cruzan umbrales de riesgo."""
import logging
import requests
import smtplib
from email.mime.text import MIMEText
from app.config import get_settings
from app.services.settings_store import load_settings

logger = logging.getLogger(__name__)

class AlertService:
    """Gestiona alertas basadas en umbrales de CRI/TMI en múltiples canales."""
    
    def __init__(self):
        self.reload_settings()
        self._last_alert_cri = None
        self._last_alert_divergence = None
    
    def reload_settings(self):
        """Carga la configuración dinámica desde el settings store y config."""
        settings = load_settings()
        sys_settings = get_settings()
        
        self.threshold = settings.get("alert_threshold", 65.0)
        self.channels = settings.get("channels", {})
        
        # Integración fallback con .env si no hay configuración específica en canales
        if sys_settings.ALERT_WEBHOOK_URL and not self.channels.get("slack", {}).get("url"):
            self.channels["slack"] = {
                "enabled": True,
                "url": sys_settings.ALERT_WEBHOOK_URL
            }
            
        logger.info(f"[ALERT] Configuración recargada. Umbral: {self.threshold}")
    
    def check_and_alert(self, cri_score: float, tmi_score: float = None):
        """
        Verifica condiciones de alerta y envia notificaciones.
        Evita spam: solo alerta cuando cruza el umbral por primera vez.
        """
        alerts = []
        
        # Alerta 1: CRI crítico
        if cri_score > self.threshold:
            if self._last_alert_cri is None or cri_score > self._last_alert_cri + 5:
                msg = f"🚨 RIESGO CRÍTICO: CRI está en {cri_score:.2f} (Umbral: {self.threshold})"
                alerts.append({"type": "critical", "message": msg})
                self._dispatch_alerts(msg)
                self._last_alert_cri = cri_score
                logger.warning(f"[ALERT] {msg}")
        else:
            self._last_alert_cri = None
        
        # Alerta 2: Divergencia CRI vs TMI
        if tmi_score is not None and abs(cri_score - tmi_score) > 40:
            if self._last_alert_divergence is None:
                msg = f"⚠️ DIVERGENCIA: CRI={cri_score:.2f} vs TMI={tmi_score:.2f} (Diferencia={abs(cri_score-tmi_score):.1f})"
                alerts.append({"type": "warning", "message": msg})
                self._dispatch_alerts(msg)
                self._last_alert_divergence = True
                logger.warning(f"[ALERT] {msg}")
        else:
            self._last_alert_divergence = None
        
        return alerts
    
    def _dispatch_alerts(self, message: str):
        """Envia el mensaje a todos los canales habilitados."""
        # 1. Slack
        slack = self.channels.get("slack", {})
        if slack.get("enabled") and slack.get("url"):
            self._send_slack(slack["url"], message)
            
        # 2. Discord
        discord = self.channels.get("discord", {})
        if discord.get("enabled") and discord.get("url"):
            self._send_discord(discord["url"], message)
            
        # 3. Telegram
        tg = self.channels.get("telegram", {})
        if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
            self._send_telegram(tg["bot_token"], tg["chat_id"], message)
            
        # 4. Email
        email = self.channels.get("email", {})
        if email.get("enabled") and email.get("smtp_server") and email.get("to_email"):
            self._send_email(email, message)
            
        # Log si no hay ningún canal habilitado
        enabled_count = sum(1 for c in self.channels.values() if c.get("enabled"))
        if enabled_count == 0:
            logger.info(f"[ALERT-DRYRUN] {message}")
            
    def _send_slack(self, url: str, message: str):
        try:
            payload = {
                "text": message,
                "username": "CRI-Metrics-Bot",
                "icon_emoji": ":warning:",
            }
            requests.post(url, json=payload, timeout=10)
            logger.info("[ALERT-SLACK] Mensaje enviado")
        except Exception as e:
            logger.error(f"[ALERT-SLACK] Error: {e}")
            
    def _send_discord(self, url: str, message: str):
        try:
            payload = {
                "content": message,
                "username": "CRI-Metrics-Bot"
            }
            requests.post(url, json=payload, timeout=10)
            logger.info("[ALERT-DISCORD] Mensaje enviado")
        except Exception as e:
            logger.error(f"[ALERT-DISCORD] Error: {e}")
            
    def _send_telegram(self, token: str, chat_id: str, message: str):
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message
            }
            requests.post(url, json=payload, timeout=10)
            logger.info("[ALERT-TELEGRAM] Mensaje enviado")
        except Exception as e:
            logger.error(f"[ALERT-TELEGRAM] Error: {e}")
            
    def _send_email(self, config: dict, message: str):
        try:
            msg = MIMEText(message)
            msg["Subject"] = "Alerta del Sistema CRI Metrics"
            msg["From"] = config.get("username", "noreply@cri-metrics.com")
            msg["To"] = config["to_email"]
            
            with smtplib.SMTP(config["smtp_server"], config.get("smtp_port", 587), timeout=15) as server:
                server.starttls()
                if config.get("username") and config.get("password"):
                    server.login(config["username"], config["password"])
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())
            logger.info("[ALERT-EMAIL] Mensaje enviado")
        except Exception as e:
            logger.error(f"[ALERT-EMAIL] Error: {e}")

# Singleton
_alert_service = AlertService()

def get_alert_service() -> AlertService:
    return _alert_service
