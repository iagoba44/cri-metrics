# Plan de Mejora - Mas Fuentes de Datos y Enriquecimiento de Prompt

## Fuentes Existentes (YA funcionando)
- Vast.ai → GSPI, UOR (GPU spot prices + occupancy)
- CoinGecko + Binance → CFBR (crypto market proxy)
- Yahoo Finance → LTCR (stock volatility: NVDA/AMD/INTC)
- WhatToMine + LambdaLabs → SHPD (hardware pricing)
- NiceHash + HuggingFace → SHPD, UOR (mining + AI trends)
- FRED → macro data
- FearGreed → sentiment
- arXiv → paper velocity
- HN Algolia → tech activity
- RSS Feeds (Reuters, TechCrunch, HN) → news pipeline

## Fuentes NUEVAS a Integrar (prioridad alta)

### 1. Google Trends (gratis, API key facil)
- **Modulo:** `app/external/google_trends.py`
- **Query:** "GPU prices", "AI chips", "NVIDIA stock", "data center"
- **KPI:** relevancia de busqueda como proxy de demanda
- **Libreria:** `pytrends` (pip install pytrends)
- **Frecuencia:** diaria/semanal

### 2. Reddit r/MachineLearning + r/nvidia (gratis, sin API key)
- **Modulo:** `app/external/reddit_trend.py`
- **Query:** "GPU", "shortage", "price", "availability"
- **KPI:** volumen posts/comentarios como proxy de hype
- **Libreria:** `asyncpraw` o scrapeo simple JSON (.json al final de URL)
- **Frecuencia:** horaria

### 3. Twitter/X Trending (gratis, rate limit alto)
- **Modulo:** buscar alternativas gratuitas a la API X
- **Alternativa:** Nitter RSS feeds anonimos
- **KPI:** volumen menciones #GPU #NVIDIA

### 4. Cloud GPU comparador (scraper)
- **Modulo:** `app/external/cloud_gpu_compare.py`
- **URLs:** 
  - `gpulist.ai` (comparador precios cloud GPU)
  - `cloudgpus.com` (disponibilidad por provider)
- **KPI:** precios y disponibilidad por region/proveedor
- **Frecuencia:** horaria

### 5. GitHub Trending AI repos (gratis)
- **Modulo:** `app/external/github_trend.py`
- **Query:** repos con "LLM", "GPU", "CUDA", "training"
- **KPI:** actividad open-source como proxy de demanda computacional
- **Frecuencia:** diaria

### 6. StackOverflow AI tags (gratis)
- **Modulo:** `app/external/stackoverflow_trend.py`
- **Query:** tags "pytorch", "tensorflow", "cuda", "gpu"
- **KPI:** preguntas/tag como proxy de adopcion
- **Frecuencia:** diaria

## Datos YA DISPONIBLES que NO se envian al prompt de Gemini

### Sistema Predictivo
- Early Warning System (autocorrelacion, varianza, aceleracion)
- TTD (Time To Danger en dias)
- Proyecciones 30/60/90d con bandas de confianza
- Probabilidad de colapso a 30d

### Sistema TMI
- 7 componentes del TMI con valores individuales
- Fear & Greed Index
- arXiv paper velocity
- HN activity level
- Global hashrate
- AI token performance
- News coverage score
- AI revenue proxies

### Sistema Algoritmico
- Z-Score volatilidad (cuantas desviaciones estandar del CRI)
- EMA suavizado (tendencia filtrada)
- Decay de pesos por fuente (confianza en cada fuente)

### Historico
- 6 meses de CRI diario con min/max
- 6 eventos de mercado detectados (NVIDIA earnings, crypto crash, etc.)
- Tendencias 7d, 30d, 90d
- Transiciones entre zonas de riesgo (LOW→MODERATE→CRITICAL)

### News Pipeline
- Articulos validados semanticamente (titulo + score)
- Sentimiento estructurado (capex, demanda, regulatorio)
- TMI news score

## Prompt Enriquecido (IMPLEMENTACION INMEDIATA)

El nuevo prompt de Gemini incluira TODOS los datos anteriores en una estructura organizada por secciones:

```
1. RESUMEN EJECUTIVO (CRI + TMI + zona + delta 24h)
2. KPIs DE ENTRADA (5 KPIs con valor, fuente, peso, frescura)
3. SISTEMA PREDICTIVO (EWS, TTD, proyecciones 30/60/90d, colapso %)
4. COMPONENTES TMI (7 sub-indices con valores)
5. INDICADORES TECNICOS (Z-Score, EMA, decay pesos)
6. HISTORICO 6 MESES (min/max CRI, tendencia, eventos de mercado)
7. NOTICIAS VALIDADAS (top headlines + sentimiento capex/demanda/reg)
8. SALUD DE FUENTES (activas/stale/offline por fuente)
```

Total datos en el prompt: ~50 campos (antes ~10)
