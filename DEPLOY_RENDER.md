# DESPLIEGUE EN RENDER.COM - INSTRUCCIONES EXACTAS

He preparado todo el proyecto para desplegar en Render.com gratuitamente.
El repositorio Git está inicializado y listo.

---

## QUE NECESITAS

1. **Cuenta de GitHub** (https://github.com/signup) — Gratis
2. **Cuenta de Render.com** (https://render.com) — Gratis
3. **Este proyecto** (ya está listo para subir)

---

## PASO 1: Subir a GitHub (5 minutos)

```bash
# 1. Ve al directorio del proyecto
cd "D:\Proyectos\METRICAS CRISS ia\cri_metrics"

# 2. Crea un repositorio en GitHub
#    - Ve a https://github.com/new
#    - Nombre: cri-metrics
#    - Descripcion: CRI Risk Index for AI Infrastructure
#    - Publico o Privado (tu eleccion)
#    - NO marques "Add a README" ni .gitignore (ya los tenemos)
#    - Click "Create repository"

# 3. Conecta tu repo local con GitHub
#    (Reemplaza TU_USUARIO por tu nombre de usuario de GitHub)
git remote add origin https://github.com/TU_USUARIO/cri-metrics.git

# 4. Sube el codigo
git branch -M main
git push -u origin main

# 5. Verifica en GitHub que todos los archivos estan subidos
#    Ve a https://github.com/TU_USUARIO/cri-metrics
```

---

## PASO 2: Crear Web Service en Render (3 minutos)

1. Ve a **https://dashboard.render.com**
2. Click **"New +"** → **"Web Service"**
3. Conecta tu cuenta de GitHub
4. Busca y selecciona el repositorio **"cri-metrics"**
5. Configura:

   | Campo | Valor |
   |-------|-------|
   | **Name** | `cri-metrics` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | **Plan** | `Free` |

6. En **Environment Variables**, agrega:
   ```
   DATABASE_URL=sqlite:///./cri_metrics.db
   ALERT_THRESHOLD=65.0
   DATA_FRESHNESS_HOURS=24
   PYTHON_VERSION=3.11
   ```

7. Opcional: Si tienes webhook de Slack/Discord para alertas:
   ```
   ALERT_WEBHOOK_URL=https://hooks.slack.com/services/TU/WEBHOOK/URL
   ```

8. Click **"Create Web Service"**

Render hará build automático y desplegará.

---

## PASO 3: URLs de tu Dashboard

Una vez desplegado (tarda 2-3 minutos):

| URL | Funcion |
|-----|---------|
| `https://cri-metrics.onrender.com/static/index.html` | **Dashboard principal** |
| `https://cri-metrics.onrender.com/api/v1/health` | Health check |
| `https://cri-metrics.onrender.com/api/v1/latest-cri` | Ultimo CRI en JSON |

**Nota importante:** En el plan gratuito, el servicio se "duerme" después de 15 minutos sin tráfico. La primera request después de dormirse tarda 30-60 segundos (cold start). Para mantenerlo despierto, puedes usar un servicio de ping gratuito como UptimeRobot.

---

## PASO 4: Activar datos en vivo

1. Abre tu dashboard
2. Click en **"Ingesta Real"** en el dashboard
3. Espera 10-20 segundos (llama a 7 fuentes externas)
4. Click en **"Calcular CRI"**
5. Verás el índice con datos reales del mercado

---

## SI HAY PROBLEMAS

### "Build failed"
Verifica que el archivo `requirements.txt` esté en la raíz del repo.

### "Module not found"
Asegúrate de que la estructura de carpetas `app/` esté subida correctamente.

### "Database error"
En plan gratuito SQLite funciona pero los datos se pierden en cada deploy. Para producción real, conecta PostgreSQL en Render (+$7/mes).

---

## PARA FORZAR ALERTAS CRITICAS (test)

Si quieres ver la alerta CRITICAL funcionando, puedes:
1. Modificar temporalmente `app/config.py` y poner `ALERT_THRESHOLD=30.0`
2. Hacer commit y push: `git add . && git commit -m "test alert" && git push`
3. Render redeployará automáticamente
4. Ejecutar ingesta + cálculo
5. Cualquier CRI > 30 disparará alerta

---

## SOPORTE

Si algo falla, el log de Render está en:
**Dashboard Render → tu servicio → Logs**

Los errores más comunes se ven ahí.
