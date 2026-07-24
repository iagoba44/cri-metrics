# CRI Metrics System

**Indice de Riesgo Compuesto (CRI) para la Medicion del Riesgo de Ajuste en Infraestructura de IA**

## Estado Actual

Sistema completo y funcional con **7 fuentes de datos reales** del mercado.

### Lectura del Mercado (Julio 2026)

```
CRI Score: 44.81
Risk Zone: MODERATE
Fuentes:   7/7 activas
```

| KPI | Valor Real | Score | Fuente |
|-----|-----------|-------|--------|
| GSPI | 81.90 | 81.90 | Vast.ai (precios spot GPU) |
| UOR  | 100.00 | 100.00 | Vast.ai (ocupacion 0%) |
| SHPD | 0.00 | 0.00 | Lambda Labs (precios cloud) |
| CFBR | 12.42 | 12.42 | CoinGecko + Binance |
| LTCR | 9.27 | 9.27 | Yahoo Finance (NVDA, SMCI, DELL) |

**Interpretacion:** Deflacion extrema en precios GPU spot (GSPI 82%) + infrautilizacion total (UOR 100%). El mercado de infraestructura IA presenta **sobreoferta severa**. Acciones IA estables (LTCR bajo) y crypto sin volatilidad extrema.

---

## Arquitectura

```
Fuentes Reales (7)
  |-> Pipeline de Ingesta
       |-> Base de Datos (SQLite/PostgreSQL)
            |-> Motor CRI (Min-Max + Ponderacion)
                 |-> API REST (FastAPI)
                      |-> Dashboard (/static/index.html)
                      |-> Alertas (Webhook)
```

---

## Fuentes de Datos Reales

| # | Fuente | KPI | Tipo | Auth |
|---|--------|-----|------|------|
| 1 | **Vast.ai** API publica | GSPI + UOR | REST JSON | No |
| 2 | **CoinGecko** API | CFBR | REST JSON | No |
| 3 | **Binance** API publica | CFBR | REST JSON | No |
| 4 | **WhatToMine** | SHPD | HTML Scraper | No |
| 5 | **Yahoo Finance** | LTCR | REST JSON | No |
| 6 | **Lambda Labs** | SHPD | HTML Scraper | No |
| 7 | **FRED (Federal Reserve)** | LTCR | REST JSON | API Key gratuita |

---

## Inicio Rapido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ver datos reales del mercado
python demo_real.py

# 3. Iniciar servidor API + Dashboard
uvicorn app.main:app --reload
# Dashboard: http://localhost:8000/static/index.html
# API docs:  http://localhost:8000/docs

# 4. Ingesta real desde 7 fuentes
curl -X POST "http://localhost:8000/api/v1/run-ingestion?use_real=true"

# 5. Calcular CRI
curl -X POST http://localhost:8000/api/v1/calculate-cri
```

---

## Dashboard

Dashboard HTML5 interactivo con:
- CRI Score en tiempo real
- Historial de CRI (grafico de lineas)
- KPIs individuales con barras de progreso
- Composicion del riesgo (grafico doughnut)
- Estado de las 7 fuentes de datos
- Log de operaciones
- Botones de control (ingesta, calculo, refresh)

---

## Tests

```bash
pytest tests/ -v
```

**Resultado:** 18/18 tests pasando.

---

## Despliegue

### Local
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker-compose up --build -d
```

### Cloud (Render.com - Gratis)
Ver `DEPLOY_RENDER.md` para pasos detallados.

---

## API Endpoints

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/v1/run-ingestion?use_real=true` | POST | Ingesta desde fuentes reales |
| `/api/v1/calculate-cri` | POST | Calcula CRI |
| `/api/v1/latest-cri` | GET | Ultimo CRI |
| `/api/v1/health` | GET | Health check |

---

## Zonas de Riesgo

- **LOW** (0-30): Mercado estable
- **MODERATE** (31-65): Presion en precios
- **CRITICAL** (66-100): Sobreoferta / compresion de margenes -> Alerta

---

## Estructura del Proyecto

```
cri_metrics/
├── app/
│   ├── main.py              # FastAPI + Dashboard
│   ├── config.py            # Settings
│   ├── database.py          # SQLAlchemy
│   ├── models.py            # TelemetryRecord, RiskIndex
│   ├── schemas.py           # Pydantic
│   ├── services/            # Motor CRI + Ingesta + Alertas
│   ├── api/v1/endpoints.py  # REST API
│   └── external/            # 7 fuentes reales + 3 simuladores
├── static/index.html        # Dashboard frontend
├── tests/                   # 18 tests
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker Compose
├── deploy.py                # Script de despliegue
├── DEPLOY_RENDER.md         # Guia Render.com
├── PLAN_IMPLANTACION.md     # Documentacion completa
├── demo.py                  # Demo simulado
└── demo_real.py             # Demo con datos reales
```

---

## Documentacion Completa

- `PLAN_IMPLANTACION.md` - Arquitectura, KPIs, formulas, despliegue
- `DEPLOY_RENDER.md` - Guia paso a paso para Render.com
- `deploy.py` - Script automatizado de despliegue

---

## Licencia

Proyecto interno - Equipo de Ingenieria de Datos / Riesgos.
