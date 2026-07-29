from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.config import get_settings
from app.services.auth import generate_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    username: str

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    settings = get_settings()
    if request.username != settings.ADMIN_USERNAME or request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    token = generate_token(request.username)
    return LoginResponse(token=token, username=request.username)

@router.get("/verify")
def verify(username: str = Depends(get_current_user)):
    return {"status": "ok", "user": username}
