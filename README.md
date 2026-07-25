# CRI Metrics System v2.5

Sistema de KPIs para la Medicion del Riesgo de Ajuste en el Mercado de Infraestructura de Inteligencia Artificial.

## Quick Start

```bash
# 1. Clonar y entrar
cd cri_metrics

# 2. Crear entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API keys (opcional pero recomendado)
cp .env.example .env
# Editar .env con tus keys

# 5. Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 6. Abrir dashboard
open http://localhost:8000/static/index.html
```

## Arquitectura

```
┌─────────────────────────────────────────┐
│           DASHBOARD (HTML/JS)           │
│  - CRI Gauge + TMI Thermometer          │
│  - Risk Donut + Data Health Heatmap      │
│  - 11 Scenarios + Historical Charts      │
│  - Alerts + Export JSON/CSV              │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         FASTAPI REST API v1             │
│  /api/v1/calculate-cri                  │
│  /api/v1/calculate-tmi                  │
│  /api/v1/run-ingestion                  │
│  /api/v1/history                        │
│  /api/v1/scenarios                      │
│  /api/v1/sources                        │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         SERVICIOS DE NEGOCIO            │
│  CRICalculator  |  TMICalculator        │
│  IngestionPipeline | AlertService       │
│  BackgroundScheduler                    │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│      13-15 FUENTES DE DATOS REALES      │
│  Sin API Key (11):                      │
│    Vast.ai, CoinGecko, Binance,         │
│    WhatToMine, YahooFinance, NiceHash,   │
│    HuggingFace, DeFiLlama, FearGreed,   │
│    arXiv, HackerNews                     │
│  Con API Key (2):                       │
│    NewsAPI, AlphaVantage                │
│  Opcionales (2):                        │
│    LambdaLabs, FRED                     │
└─────────────────────────────────────────┘
```

## Indicadores

### CRI (Composite Risk Index)
Indice compuesto de riesgo (0-100) basado en 5 KPIs ponderados:

| KPI | Descripcion | Peso | Fuente |
|-----|-------------|------|--------|
| GSPI | GPU Spot Price Index (% deflacion) | 25% | Vast.ai |
| SHPD | Server Hardware Price Deflation | 15% | WhatToMine + LambdaLabs |
| LTCR | Long-Term Contract Ratio | 20% | YahooFinance (NVDA, AMD, etc.) |
| CFBR | Cloud Free-Burn Rate | 20% | CoinGecko + Binance |
| UOR  | Underutilization/Overcapacity | 20% | Vast.ai |

**Zonas:**
- **LOW (0-30):** Mercado estable
- **MODERATE (31-65):** Presion detectada
- **CRITICAL (66-100):** Sobreoferta o compresion extrema

### TMI (Temperature Market Index)
Indice de temperatura de mercado IA (0-100) con 6-7 componentes:

| Componente | Descripcion | Peso |
|------------|-------------|------|
| Fear & Greed | Sentimiento crypto | 25% |
| arXiv Velocity | Papers ML/24h | 20% |
| HN Activity | Menciones IA en HN | 15% |
| Hashrate | Infraestructura GPU activa | 15% |
| AI Tokens | Performance tokens IA | 10% |
| News Coverage | Articulos IA/24h | 15% |
| AI Revenue | Ingresos empresas IA (opcional) | - |

**Zonas:** COLD (0-30), WARM (31-70), HOT (71-100)

## API Keys

Algunas fuentes requieren API keys gratuitas:

| Servicio | URL | Key gratis |
|----------|-----|------------|
| NewsAPI | https://newsapi.org | 100 req/dia |
| AlphaVantage | https://alphavantage.co | 25 req/dia |

Crear archivo `.env`:
```
NEWSAPI_KEY=tu_key_aqui
ALPHAVANTAGE_KEY=tu_key_aqui
ALERT_WEBHOOK_URL=https://hooks.slack.com/...  # opcional
```

## Docker

```bash
docker-compose up -d
```

Servicios:
- `cri-api`: FastAPI en puerto 8000
- Opcional: PostgreSQL en lugar de SQLite

## Tests

```bash
pytest tests/ -v
```

## Endpoints principales

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | /api/v1/calculate-cri | Calcula CRI actual |
| GET | /api/v1/calculate-tmi | Calcula TMI actual |
| POST | /api/v1/run-ingestion | Ingesta datos en tiempo real |
| GET | /api/v1/history | Historial 24h CRI/TMI |
| GET | /api/v1/scenarios | Lista 11 escenarios |
| POST | /api/v1/simulate-scenario | Activa simulacion |
| GET | /api/v1/sources | Estado de fuentes |
| GET | /api/v1/mode | Modo actual (REAL/SIM) |

## Escenarios (11)

1. **Mercado Normal** - Condiciones estables
2. **Escasez GPU** - Demanda masiva
3. **Crash Crypto** - Colapso crypto
4. **Bear Market** - Contraccion general
5. **Bull Run** - Inversion masiva
6. **Crisis Suministro** - Problemas cadena
7. **Shock Regulatorio** - Nuevas leyes
8. **Boom Infraestructura** - Mega data centers
9. **Invierno IA** - Desilusion con IA
10. **Crisis Energetica** - Precios energia altos
11. **AI Utopia** - Hype real, mercado sano (CRI bajo)

## Alertas

El sistema genera alertas automaticas cuando:
- CRI > 65 (CRITICAL RISK)
- Divergencia TMI vs CRI > 40 puntos

Webhook configurable via `ALERT_WEBHOOK_URL` en `.env`.

## Licencia

MIT License - CRI Infrastructure Intelligence 2024
