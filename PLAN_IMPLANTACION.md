# Plan de Implantación - Sistema CRI (Composite Risk Index)

## 1. Resumen Ejecutivo

Este documento describe el plan de implantación del **Sistema de KPIs para la Medición del Riesgo de Ajuste en IA**, que calcula un Índice de Riesgo Compuesto (CRI) a partir de 5 KPIs clave del mercado de infraestructura de IA.

**Zonas de Riesgo:**
- **LOW**: 0 - 30
- **MODERATE**: 31 - 65
- **CRITICAL**: 66 - 100 (dispara alertas)

---

## 2. Arquitectura del Sistema

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Fuentes       │     │   Pipeline      │     │   Motor         │
│   Reales        │────▶│   de Ingesta    │────▶│   de Calculo    │
│   (7 fuentes)   │     │                 │     │   CRI           │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Vast.ai (API)   │     │ SQLite/PostgreSQL│    │ Normalizacion   │
│ CoinGecko (API) │     │ TelemetryRecord  │    │ Min-Max         │
│ Binance (API)   │     │ RiskIndex        │    │ Ponderacion     │
│ WhatToMine      │     └─────────────────┘     └─────────────────┘
│ Yahoo Finance   │                                   │
│ Lambda Labs     │                                   ▼
│ FRED (Fed)      │                       ┌─────────────────┐
└─────────────────┘                       │   API REST +    │
                                          │   Dashboard     │
                                          │   FastAPI       │
                                          └─────────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │  Sistema de     │
                                          │  Alertas        │
                                          │  Webhook/Email  │
                                          └─────────────────┘
```

---

## 3. KPIs y Fórmulas de Medición

### 3.1 Definición de KPIs

| Código | Nombre | Descripción | Fuente | Fórmula | Peso |
|--------|--------|-------------|--------|---------|------|
| **GSPI** | GPU Spot Price Index | Índice de deflación de precios spot GPU | SEC EDGAR / Mercados | Inverso: mayor deflación = mayor riesgo | 0.25 |
| **SHPD** | Server Hardware Price Deflation | Deflación en precios de hardware servidor | B2B Scrapers | Directo: mayor deflación = mayor riesgo | 0.15 |
| **LTCR** | Long-Term Contract Ratio | Ratio de contratos a largo plazo | SEC EDGAR | Inverso: mayor ratio = mayor riesgo de compresión | 0.20 |
| **CFBR** | Cloud Free-Burn Rate | Tasa de quema de capital operativo | Neoclouds API | Directo: mayor quema = mayor riesgo | 0.20 |
| **UOR** | Underutilization/Overcapacity Ratio | Ratio de infrautilización/sobrecapacidad | Neoclouds API | Directo: mayor ratio = mayor riesgo | 0.20 |

### 3.2 Normalización Min-Max

**Fórmula Directa** (SHPD, CFBR, UOR):
```
normalized_score = (raw_value - min) / (max - min) * 100
```

**Fórmula Inversa** (GSPI, LTCR):
```
normalized_score = (raw_value - min) / (max - min) * 100
```
> Nota: En este dominio, tanto GSPI como LTCR usan mapeo directo donde el valor máximo del raw representa el máximo riesgo. La "inversa" del SDD se refiere a que el extremo de mayor riesgo se mapea a 100.

**Truncamiento OUT_OF_BOUNDS:**
- Si `raw_value < min` → score = 0
- Si `raw_value > max` → score = 100

### 3.3 Cálculo del CRI

```
CRI = GSPI_score * 0.25 +
      SHPD_score * 0.15 +
      LTCR_score * 0.20 +
      CFBR_score * 0.20 +
      UOR_score  * 0.20
```

**Ejemplo práctico:**
| KPI | Raw | Score | Peso | Contribución |
|-----|-----|-------|------|--------------|
| GSPI | 35.0 | 35.00 | 0.25 | 8.75 |
| SHPD | 18.5 | 37.00 | 0.15 | 5.55 |
| LTCR | 72.0 | 72.00 | 0.20 | 14.40 |
| CFBR | 82.5 | 82.50 | 0.20 | 16.50 |
| UOR | 45.0 | 45.00 | 0.20 | 9.00 |
| **CRI Total** | | | | **54.20** |

**Zona:** MODERATE (31-65)

---

## 4. Plan de Implantación Paso a Paso

### Fase 1: Preparación del Entorno (Día 1)

```bash
# 1. Clonar o crear el directorio del proyecto
cd cri_metrics

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Verificar instalación
pytest tests/ -v
```

### Fase 2: Configuración (Día 1-2)

Crear archivo `.env` en la raíz:
```env
DATABASE_URL=sqlite:///./cri_metrics.db
ALERT_THRESHOLD=65.0
DATA_FRESHNESS_HOURS=24
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Para producción (PostgreSQL):**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/cri_db
```

### Fase 3: Fuentes de Datos Reales (YA IMPLEMENTADAS)

El sistema incluye **7 fuentes reales** en `app/external/`:

| # | Fuente | KPI | Tipo | Auth | Archivo |
|---|--------|-----|------|------|---------|
| 1 | **Vast.ai** API pública | GSPI + UOR | REST JSON | No | `vast_ai_live.py` |
| 2 | **CoinGecko** API | CFBR | REST JSON | No | `coingecko.py` |
| 3 | **Binance** API pública | CFBR | REST JSON | No | `binance.py` |
| 4 | **WhatToMine** | SHPD | HTML Scraper | No | `whattomine.py` |
| 5 | **Yahoo Finance** | LTCR | REST JSON | No | `yahoo_finance.py` |
| 6 | **Lambda Labs** | SHPD | HTML Scraper | No | `lambdalabs.py` |
| 7 | **FRED (Fed)** | LTCR | REST JSON | API Key gratuita | `fred_macro.py` |

#### Fuentes adicionales recomendadas (futuro)
- **SEC EDGAR XBRL:** Filings contractuales de NVDA, SMCI, DELL
- **RunPod API:** `https://rest.runpod.io/v1/` (requiere API key)
- **Scrapers B2B:** Dell/HP pricing portals, Alibaba Cloud pricing
- **Glassnode/Messari:** Datos on-chain para correlación GPU-crypto

### Fase 4: Despliegue de la API (Día 2-3)

```bash
# Desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción (con múltiples workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Endpoints disponibles:**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | **Dashboard UI** (redirige a /static/index.html) |
| GET | `/static/index.html` | **Dashboard CRI** con gráficos en vivo |
| POST | `/api/v1/calculate-cri` | Calcula el índice CRI actual |
| POST | `/api/v1/ingest` | Ingesta manual de telemetría |
| POST | `/api/v1/run-ingestion?use_real=true` | Ingesta desde fuentes **reales** |
| GET | `/api/v1/latest-cri` | Obtiene el último CRI calculado |
| GET | `/api/v1/health` | Health check |

### Fase 5: Orquestación y Scheduling (Día 4-5)

**Opción A: Cron + curl**
```bash
# Crontab - cada hora
0 * * * * curl -X POST http://localhost:8000/api/v1/run-ingestion
5 * * * * curl -X POST http://localhost:8000/api/v1/calculate-cri
```

**Opción B: APScheduler (incluido en requirements)**
```python
# Agregar a main.py o crear scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.ingestion import IngestionPipeline
from app.services.calculator import CRICalculator

def scheduled_job():
    db = next(get_db())
    pipeline = IngestionPipeline(db)
    pipeline.run_scheduled_ingestion()
    calculator = CRICalculator(db)
    calculator.calculate()

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, 'interval', hours=1)
scheduler.start()
```

**Opción C: Apache Airflow (recomendado para escala)**
- Crear DAGs para ingesta y cálculo
- Monitoreo nativo de fallos
- Retry policies

### Fase 6: Monitoreo y Alertas (Día 5-7)

**Alertas configurables:**
- Umbral CRI > 65 → CRITICAL
- Webhook a Slack/Teams/PagerDuty
- Email simulado (en producción, integrar SMTP)

**Logs estructurados:**
- Alertas CRITICAL se loguean en JSON
- Componentes: `app/services/alerts.py`

**Dashboards recomendados:**
- Grafana + PostgreSQL datasource
- Metabase
- Custom BI conectado a `/api/v1/latest-cri`

---

## 5. Cómo Medir las Métricas en Producción

### 5.1 Proceso de Medición

1. **Extracción:** Los pipelines (`run-ingestion`) obtienen datos cada hora desde las APIs externas.
2. **Almacenamiento:** Cada lectura se guarda como `TelemetryRecord` con `raw_value`, `kpi_code`, `timestamp` y `data_source`.
3. **Normalización:** Al calcular CRI, cada `raw_value` se transforma en `normalized_score` [0-100] usando Min-Max.
4. **Composición:** Se aplica ponderación y se obtiene el `cri_score`.
5. **Clasificación:** Se determina `risk_zone` según umbrales.
6. **Alerta:** Si CRITICAL, se dispara alerta con KPIs detonantes.

### 5.2 Frecuencia Recomendada

| KPI | Frecuencia | Fuente Primaria |
|-----|-----------|-----------------|
| GSPI | Diaria | SEC EDGAR (filings), mercados spot |
| SHPD | Semanal | Scrapers B2B, portales OEM |
| LTCR | Trimestral | SEC EDGAR (10-K, 10-Q) |
| CFBR | Diaria | Neocloud APIs, dashboards |
| UOR | Horaria | Neocloud APIs, telemetry |

### 5.3 Manejo de Datos Faltantes (MISSING_DATA)

Si una fuente falla:
1. El sistema usa el último `TelemetryRecord` válido disponible.
2. Se marca como `freshness_flag = "STALE"`.
3. Se registra warning en logs.
4. El cálculo continúa sin interrupción.

---

## 6. Estrategia de Testing

```bash
# Tests unitarios
pytest tests/test_normalizer.py -v
pytest tests/test_calculator.py -v
pytest tests/test_ingestion.py -v

# Tests de API (integración)
pytest tests/test_api.py -v

# Todos los tests
pytest tests/ -v
```

**Cobertura validada:**
- Regla 1 (Fórmula Inversa): GSPI, LTCR
- Regla 2 (Fórmula Directa): SHPD, CFBR, UOR
- Regla 3 (Ponderación): Suma ponderada exacta
- OUT_OF_BOUNDS: Truncamiento a 0/100
- MISSING_DATA: Uso de datos stale
- Escenario Moderate: CRI ≤ 65
- Escenario Critical: CRI > 65 + alertas

---

## 7. Escalabilidad y Producción

### 7.1 Base de Datos

**Desarrollo:** SQLite (incluido)
**Producción:** PostgreSQL 14+

Migración:
```bash
# 1. Cambiar DATABASE_URL en .env
# 2. Ejecutar Alembic (opcional)
alembic init migrations
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### 7.2 Contenerizacion (Docker + Compose)

**Archivos incluidos:**
- `Dockerfile` - Imagen Python 3.11 + FastAPI
- `docker-compose.yml` - Servicio API con healthcheck

```bash
# Construir y desplegar
docker-compose up --build -d

# Ver logs
docker-compose logs -f cri-api

# Detener
docker-compose down
```

### 7.3 Despliegue en la Nube (Gratuito)

#### Opcion A: Render.com (Recomendado - Gratis)
```bash
# Ver DEPLOY_RENDER.md para pasos detallados
# Dashboard en: https://render.com
# Plan Free con PostgreSQL opcional (+$7/mes)
```

#### Opcion B: Railway.app
```bash
# Ver deploy.py para guia
# Variables de entorno via dashboard
```

#### Opcion C: VPS (DigitalOcean, AWS EC2, Hetzner)
```bash
# Clonar repo
# docker-compose up -d
# Nginx reverse proxy + SSL (Certbot)
```

---

## 8. Checklist de Go-Live

- [x] Tests pasan (`pytest tests/` -> 18/18 passed)
- [x] Fuentes externas **reales** integradas (7 fuentes)
- [x] Dashboard frontend funciona (`/static/index.html`)
- [ ] `.env` configurado con DB PostgreSQL (produccion)
- [ ] Scheduling configurado (cron/APScheduler)
- [ ] Alertas testeadas (forzar CRI > 65)
- [ ] Webhook de alertas configurado
- [ ] Desplegado en Render/Railway/VPS
- [ ] SSL/HTTPS configurado

---

## 9. Comandos Rápidos

```bash
# Instalar
pip install -r requirements.txt

# Correr tests
pytest tests/ -v

# Iniciar servidor (con dashboard)
uvicorn app.main:app --reload
# Dashboard: http://localhost:8000/static/index.html
# API docs:  http://localhost:8000/docs

# Demo con datos reales del mercado
python demo_real.py

# Ingesta REAL desde 7 fuentes externas
curl -X POST "http://localhost:8000/api/v1/run-ingestion?use_real=true"

# Calcular CRI con datos reales
curl -X POST http://localhost:8000/api/v1/calculate-cri

# Ver ultimo CRI
curl http://localhost:8000/api/v1/latest-cri

# Docker despliegue
docker-compose up --build -d
```

---

## 10. Contacto y Mantenimiento

- **Equipo:** Ingeniería de Datos / Riesgos
- **Repositorio:** `cri_metrics/`
- **Issues:** Crear tickets para fallos de fuentes de datos
- **Revisión:** Revisar bounds de KPIs trimestralmente según condiciones de mercado
