"""Módulo de autenticación simple sin dependencias externas."""
import hmac
import hashlib
import time
import base64
import json
from fastapi import Header, HTTPException, Depends
from app.config import get_settings

def generate_token(username: str) -> str:
    settings = get_settings()
    payload = {
        "user": username,
        "exp": int(time.time()) + 86400  # Token expira en 24 horas
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{payload_b64}.{signature_b64}"

def verify_token(token: str) -> dict:
    settings = get_settings()
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature_b64 = parts
        
        # Validar firma
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None
        
        # Decodificar payload
        padding = 4 - (len(payload_b64) % 4)
        if padding < 4:
            payload_b64 += "=" * padding
            
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        
        # Verificar expiración
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None

def get_current_user(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="No se proporcionó token de autenticación")
    
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
        
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
        
    return payload["user"]
