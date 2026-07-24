@echo off
chcp 65001 >nul
echo ==========================================
echo  PUSH A GITHUB - CRI METRICS
echo ==========================================
echo.
echo Tu repo es PRIVADO. Git te pedira login.
echo.
echo Opciones de login:
echo   1. Usuario: IAGOBA44
echo   2. Password: Tu Personal Access Token (PAT)
echo.
echo Si no tienes PAT:
echo   - Ve a https://github.com/settings/tokens
echo   - Click "Generate new token (classic)"
echo   - Marca SOLO "repo"
echo   - Copia el token y pegalo como password aqui
echo.
echo ==========================================
echo.

cd /d "D:\Proyectos\METRICAS CRISS ia\cri_metrics"

echo [1/3] Configurando remote...
git remote remove origin 2>nul
git remote add origin https://github.com/IAGOBA44/cri-metrics.git

echo [2/3] Cambiando a rama main...
git branch -M main

echo [3/3] Haciendo push... (te pedira usuario/token)
echo.
git push -u origin main

echo.
echo ==========================================
if %errorlevel% == 0 (
    echo  ✅ PUSH EXITOSO
    echo  Verifica: https://github.com/IAGOBA44/cri-metrics
) else (
    echo  ❌ Error en push
    echo  Si fallo por auth, asegurate de usar tu PAT como password
)
echo ==========================================
echo.
pause
