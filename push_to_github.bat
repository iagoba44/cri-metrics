@echo off
chcp 65001 >nul
echo ==========================================
echo  PUSH A GITHUB - CRI METRICS v2
echo ==========================================
echo.
echo IMPORTANTE: Tu repo es PRIVADO.
echo Necesitas un Personal Access Token (PAT).
echo.
echo 1. Ve a: https://github.com/settings/tokens
echo 2. Click "Generate new token (classic)"
echo 3. Marca SOLO "repo"
echo 4. Copia el token
echo 5. Cuando este script pida password, PEGA el token (NO tu contrasena de GitHub)
echo.
echo Usuario: IAGOBA44
echo Repo: cri-metrics
echo ==========================================
echo.

cd /d "D:\Proyectos\METRICAS CRISS ia\cri_metrics"

echo [1/3] Configurando remote...
git remote remove origin 2>nul
git remote add origin https://github.com/IAGOBA44/cri-metrics.git

echo [2/3] Cambiando a rama main...
git branch -M main

echo [3/3] Haciendo push...
echo.
echo CUANDO PIDA PASSWORD, PEGA TU PERSONAL ACCESS TOKEN
echo.
git push -u origin main

echo.
echo ==========================================
if %errorlevel% == 0 (
    echo  PUSH EXITOSO!
    echo  Verifica: https://github.com/IAGOBA44/cri-metrics
) else (
    echo  ERROR en push
    echo  Si fallo por autenticacion:
    echo    1. Ve a https://github.com/settings/tokens
    echo    2. Genera un token con permiso "repo"
    echo    3. Ejecuta este script de nuevo
    echo.
    echo  ALTERNATIVA: Sube manualmente via web:
    echo    https://github.com/IAGOBA44/cri-metrics/upload
)
echo ==========================================
echo.
pause
