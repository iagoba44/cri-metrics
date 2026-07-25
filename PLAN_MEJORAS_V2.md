# PLAN DE MEJORAS V2 - Temperatura del Mercado IA

## Fecha: 2026-07-25
## Version: CRI Metrics v2.3 -> v2.4

---

## 1. RESUMEN DEL ESTADO ACTUAL (v2.3)

**Fuentes activas:** 10 APIs externas
**KPIs:** GSPI, SHPD, LTCR, CFBR, UOR
**Modos:** REAL (10 APIs) + SIMULATION (10 escenarios)
**Pipeline:** Consenso automático con std_dev alerta >30

**Problema identificado:** Medimos bien el *riesgo* pero no la *temperatura* del mercado. 
Falta capturar:
- **Sentimiento / psicología** del mercado (miedo vs codicia)
- **Actividad académica/R&D** (publicaciones, repos)
- **Actividad social/técnica** (noticias, HN, trends)
- **Métricas de infraestructura activa** (hashrate, dificultad, pools)
- **Noticias de data centers** (expansiones, cierres, lead times)

---

## 2. QUÉ FALTA MEDIR PARA "TEMPERATURA DEL MERCADO"

### 2.1 Sentimiento del Mercado Crypto (ya parcialmente cubierto por CFBR)
| Métrica | Qué mide | Fuente verificada |
|---|---|---|
| Fear & Greed Index | 0-100, miedo vs codicia crypto | ✅ alternative.me/fng/ (API pública, sin key) |
| AI token prices | Capitalización proyectos IA en crypto | ✅ CoinGecko /coins/markets category=AI |
| HN stories count | Interés técnico en IA/GPU | ✅ hn.algolia.com/api (API pública) |

### 2.2 Actividad Académica / R&D
| Métrica | Qué mide | Fuente verificada |
|---|---|---|
| arXiv cs.LG papers/day | Velocidad de investigación ML | ✅ export.arxiv.org/api (sin key, 100+ papers/día) |
| GitHub LLM repos | Actividad open-source IA | ✅ api.github.com (60 req/h sin auth) |
| HuggingFace models/day | Nuevos modelos subidos | ✅ huggingface.co/api/trending (ya implementado) |

### 2.3 Infraestructura Activa / Minería
| Métrica | Qué mide | Fuente verificada |
|---|---|---|
| NiceHash hashrate | GPUs trabajando globalmente | ✅ api2.nicehash.com (ya implementado) |
| MiningPoolStats | Estado pools GPU | ✅ miningpoolstats.stream (scraper web) |
| Network difficulty | GPUs conectadas a redes | ❌ Ravencoin API caído. Alternativa: WhatToMine (ya tenemos) |

### 2.4 Noticias de Data Centers / Cloud
| Métrica | Qué mide | Fuente verificada |
|---|---|---|
| NewsAPI - "data center expansion" | Expansiones/cierres DC | ⚠️ newsapi.org (requiere API key gratuita) |
| Google Trends - "data center GPU" | Interés público en infra IA | ⚠️ pytrends (sin API key, puede fallar por rate limit) |
| Alpha Vantage - NVDA earnings | Revenue data center segment | ⚠️ alphavantage.co (requiere API key gratuita) |
| EIA API - electricity prices | Costo energía para DC | ⚠️ eia.gov/opendata (requiere API key gratuita) |

### 2.5 Métricas de Empleo / Inversión
| Métrica | Qué mide | Fuente verificada |
|---|---|---|
| Adzuna - ML jobs | Demanda talento IA | ⚠️ requiere API key gratuita |
| LinkedIn - AI job posts | Ofertas trabajo ML/LLM | ❌ LinkedIn bloquea scraping masivo |
| Crunchbase - AI funding | Inversión VC en IA | ❌ API paga ($500+/mes) |

---

## 3. PROPUESTA: NUEVO KPI "TMI" - Temperature Market Index

### Concepto
El TMI es un **KPI complementario** al CRI (no reemplaza ninguno). Mide qué tan "caliente" está el mercado IA en este momento.

- **TMI ALTO (70-100)** = Mercado muy activo: muchos papers, hashrate alto, noticias positivas, expansión DC
- **TMI MEDIO (30-70)** = Mercado estable
- **TMI BAJO (0-30)** = Mercado frío: poca actividad, desinterés, hashrate bajo

### Fórmula propuesta
```
TMI = (FearGreed_inv * 0.30) + (Arxiv_velocity * 0.25) + (HN_activity * 0.20) + (Hashrate_proxy * 0.15) + (AI_tokens_performance * 0.10)
```

Donde:
- **FearGreed_inv** = 100 - Fear&Greed Index (invertido: miedo=frío, codicia=caliente)
- **Arxiv_velocity** = papers cs.LG últimas 24h escalado a 0-100
- **HN_activity** = stories IA/GPU últimas 24h escalado a 0-100
- **Hashrate_proxy** = hashrate global NiceHash escalado a 0-100
- **AI_tokens_performance** = performance media tokens IA (CoinGecko) escalado

### Fuentes para TMI (todas verificadas SIN API key)
| Fuente | URL | Métrica | Estado |
|---|---|---|---|
| Fear & Greed | api.alternative.me/fng/ | 0-100 índice | ✅ Funciona |
| arXiv | export.arxiv.org/api | papers cs.LG últimas 24h | ✅ Funciona (100 papers/día) |
| HN Algolia | hn.algolia.com/api | stories AI/GPU | ✅ Funciona (3800+ stories) |
| NiceHash | api2.nicehash.com | hashrate global | ✅ Ya implementado |
| CoinGecko AI | /coins/markets?category=AI | precios tokens IA | ✅ Funciona |

---

## 4. SISTEMA DE PONDERACIÓN DE FUENTES (Feature Request)

### Problema actual
Todas las fuentes de un KPI tienen el mismo peso en el promedio. 
Ejemplo: HuggingFace (proxy indirecto de UOR) pesa igual que Vast.ai (datos directos).

### Solución propuesta
Archivo `app/services/source_weights.py` ya creado con pesos recomendados:

| KPI | Fuente | Peso | Justificación |
|---|---|---|---|
| GSPI | Vast.ai | 1.0 | Datos directos de marketplace |
| SHPD | NiceHash | 0.9 | API pública robusta, hashrate real |
| SHPD | WhatToMine | 0.8 | Scraper confiable pero puede fallar |
| SHPD | HuggingFace | 0.4 | Proxy indirecto (tamaño modelos) |
| SHPD | LambdaLabs | 0.3 | Scraping difícil, web bloquea |
| UOR | Vast.ai | 1.0 | Datos directos de ocupación |
| UOR | NiceHash | 0.7 | Hashrate como proxy indirecto |
| UOR | HuggingFace | 0.3 | Downloads muy indirecto |
| CFBR | CoinGecko | 1.0 | Datos globales crypto confiables |
| CFBR | Binance | 0.9 | Ticker preciso ETH |
| CFBR | DeFiLlama | 0.7 | TVL como proxy macro |
| CFBR | DeFiLlama_VOL | 0.4 | Volatilidad chains, más ruido |
| LTCR | Yahoo Finance | 1.0 | API estable, stocks reales |
| LTCR | FRED | 0.5 | Requiere API key |

### Implementación
Modificar `ingestion.py` fase 2 de deduplicación para usar `compute_weighted_average()` en lugar de promedio simple.

---

## 5. ROADMAP DE IMPLEMENTACIÓN

### Fase 1: Ponderación de fuentes (1-2h)
- [ ] Integrar `source_weights.py` en pipeline de deduplicación
- [ ] Añadir endpoint `/source-weights` para consultar/configurar pesos
- [ ] Actualizar dashboard para mostrar pesos de cada fuente

### Fase 2: Temperatura del mercado - TMI (2-3h)
- [ ] Crear cliente `app/external/fear_greed.py` (Alternative.me)
- [ ] Crear cliente `app/external/arxiv_trend.py` (papers velocity)
- [ ] Crear cliente `app/external/hackernews.py` (stories count)
- [ ] Crear cliente `app/external/coingecko_ai.py` (AI tokens performance)
- [ ] Crear calculador `app/services/tmi_calculator.py`
- [ ] Añadir KPI TMI al CRI (como métrica adicional) o como índice separado
- [ ] Añadir endpoint `/calculate-tmi`
- [ ] Añadir TMI al dashboard

### Fase 3: Fuentes con API key opcionales (2-3h, post-v2.4)
- [ ] NewsAPI - noticias data centers (requiere key gratuita)
- [ ] Alpha Vantage - earnings NVDA (requiere key gratuita)
- [ ] Google Trends - pytrends (sin key pero rate limit)
- [ ] EIA - precios electricidad (requiere key gratuita)
- [ ] Documentar cómo configurar keys en `.env`

### Fase 4: Alertas inteligentes (1-2h, post-v2.4)
- [ ] Alerta cuando TMI > 80 y CRI < 30 = "Mercado sobrecalentado, riesgo de burbuja"
- [ ] Alerta cuando TMI < 20 y CRI > 70 = "Mercado frío con alto riesgo = posible colapso"
- [ ] Alerta cuando TMI diverge del CRI > 40 puntos = desconexión temperatura/riesgo

---

## 6. DECISIONES PENDIENTES PARA EL USUARIO

### Pregunta 1: ¿Implementar TMI como KPI separado o integrarlo en CRI?
- **Opción A (recomendada)**: TMI como índice **independiente** (dashboard muestra CRI + TMI lado a lado)
- **Opción B**: Integrar TMI como 6º componente del CRI (complica la fórmula existente)

### Pregunta 2: ¿Prioridad de implementación?
- **Opción A**: Fase 1 (ponderación) + Fase 2 (TMI) AHORA -> v2.4
- **Opción B**: Solo Fase 1 (ponderación) ahora, TMI más adelante
- **Opción C**: Solo TMI ahora, ponderación más adelante
- **Opción D**: Todo ahora (Fase 1 + 2, ~3-4h de trabajo)

### Pregunta 3: ¿Qué fuentes con API key quieres integrar?
- NewsAPI (noticias) - key gratuita en newsapi.org
- Alpha Vantage (earnings) - key gratuita en alphavantage.co
- EIA (electricidad) - key gratuita en eia.gov/opendata
- Google Trends - sin key pero menos fiable

### Pregunta 4: ¿Ajustar pesos de fuentes?
- ¿Dar más peso a Vast.ai para UOR? (actual 1.0, máximo)
- ¿Reducir peso de HuggingFace para SHPD? (actual 0.4)
- ¿Añadir peso manual configurable vía API?

---

## 7. CHECKLIST DE FUENTES VERIFICADAS (Actualizado v2.3)

| # | Fuente | KPI | Método | Auth | Estado |
|---|---|---|---|---|---|
| 1 | Vast.ai | GSPI, UOR | API pública | No | ✅ Activa |
| 2 | CoinGecko | CFBR | API pública | No | ✅ Activa |
| 3 | Binance | CFBR | API pública | No | ✅ Activa |
| 4 | WhatToMine | SHPD | Scraper web | No | ✅ Activa |
| 5 | Yahoo Finance | LTCR | API pública | No | ✅ Activa |
| 6 | Lambda Labs | SHPD | Scraper web | No | ⚠️ Intermitente |
| 7 | NiceHash | SHPD, UOR | API pública | No | ✅ Activa |
| 8 | HuggingFace | UOR, SHPD | API pública | No | ✅ Activa |
| 9 | DeFiLlama | CFBR | API pública | No | ✅ Activa |
| 10 | Fear & Greed | TMI | API pública | No | ✅ Verificada |
| 11 | arXiv | TMI | API pública | No | ✅ Verificada |
| 12 | HN Algolia | TMI | API pública | No | ✅ Verificada |
| 13 | CoinGecko AI | TMI | API pública | No | ✅ Verificada |
| 14 | NewsAPI | Noticias DC | API key gratuita | Sí | ⚠️ Requiere key |
| 15 | Alpha Vantage | Earnings | API key gratuita | Sí | ⚠️ Requiere key |
| 16 | EIA | Energía DC | API key gratuita | Sí | ⚠️ Requiere key |
| 17 | Google Trends | Interés público | Sin key | No | ⚠️ Rate limit |

---

## 8. CONCLUSIÓN

**Para medir la temperatura real del mercado IA, necesitamos:**

1. **TMI (Temperature Market Index)** basado en 5 fuentes públicas verificadas
2. **Ponderación de fuentes** para que Vast.ai/NiceHash pesen más que proxies indirectos
3. **APIs adicionales con key gratuita** para noticias DC y earnings

**Todo es implementable sin costo** (APIs públicas o keys gratuitas).

**Tiempo estimado:** 3-4h para Fase 1 + 2 (ponderación + TMI).
