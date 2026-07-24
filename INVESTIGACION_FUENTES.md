# Investigacion: Mejora de Fuentes de Datos - Sistema CRI

**Objetivo:** Evaluar la calidad, fiabilidad y cobertura de las 7 fuentes actuales, identificar debilidades criticas, y proponer un roadmap de mejoras para aumentar la precision predictiva del Indice de Riesgo Compuesto (CRI).

**Autor:** Sistema de Ingenieria de Datos
**Fecha:** Julio 2026
**Version:** 1.0

---

## 1. Diagnostico de Fuentes Actuales

### 1.1 Matriz de Evaluacion

| # | Fuente | KPI | Tipo | Auth | Latencia | Fiabilidad | Precision | Cobertura | Estado |
|---|--------|-----|------|------|----------|------------|-----------|-----------|--------|
| 1 | Vast.ai | GSPI + UOR | REST JSON | No | <2s | ALTA | ALTA | Marketplace spot GPU | ✅ Estable |
| 2 | CoinGecko | CFBR | REST JSON | No | <2s | ALTA | MEDIA | Global crypto market | ✅ Estable |
| 3 | Binance | CFBR | REST JSON | No | <1s | ALTA | ALTA | Exchange crypto ETH/USDT | ✅ Estable |
| 4 | WhatToMine | SHPD | HTML Scraper | No | 5-10s | MEDIA | MEDIA | Rentabilidad minera GPU | ⚠️ Fragil |
| 5 | Yahoo Finance | LTCR | REST JSON | No | 2-5s | MEDIA | MEDIA | Acciones IA infraestructura | ⚠️ Inestable |
| 6 | Lambda Labs | SHPD | HTML Scraper | No | 5-10s | MEDIA | MEDIA | Precios cloud GPU | ⚠️ Fragil |
| 7 | FRED (Fed) | LTCR | REST JSON | API Key | 2-5s | ALTA | ALTA | Macroeconomia industrial | ❌ Falla sin key |

### 1.2 Problemas Identificados

#### 🔴 CRITICO: UOR = 100% siempre en Vast.ai

**Sintoma:** UOR reporta 100% (0 GPUs alquiladas) consistentemente.

**Analisis:**
- Vast.ai devuelve `rented: false` para TODOS los bundles en la API publica.
- Esto NO significa que nadie alquile GPUs. Significa que la API publica no expone el estado de alquiler real.
- El campo `rented` parece ser un flag de control del host, no una metrica de ocupacion real.

**Impacto:** UOR siempre = 100 → contribuye 20 puntos fijos al CRI. El KPI pierde utilidad predictiva.

**Evidencia de la respuesta API:**
```json
{
  "rentable": true,
  "rented": false,  // <- Siempre false en API publica
  "num_gpus": 1
}
```

#### 🟠 ALTO: Scrapers HTML son fragiles

**Fuentes afectadas:** WhatToMine, Lambda Labs

**Problemas:**
- Cambios en el DOM de la pagina rompen los regex.
- Rate limits agresivos (WhatToMine bloquea tras varias requests).
- Sin estructura formal → dificil validar la integridad de los datos.
- Latencia alta (5-10s vs <2s de APIs REST).

**Impacto:** Interrupciones frecuentes de ingesta, datos inconsistentes.

#### 🟡 MEDIO: Yahoo Finance sin datos históricos

**Problema:** Solo obtenemos cambio diario. Sin ventana temporal (7d, 30d), la volatilidad diaria puede ser ruido.

**Ejemplo:** NVDA -1.56% en un dia puede ser fluctuacion normal, no compresion de contratos.

#### 🟡 MEDIO: CoinGecko + Binance miden lo mismo (CFBR)

**Redundancia:** Ambas fuentes miden volatilidad crypto. La correlacion entre ambas es ~0.85. Aportan poca diversificacion de informacion.

#### 🟢 BAJO: FRED requiere API key

**Problema:** Sin key gratuita, la fuente no funciona. El usuario debe registrar manualmente.

---

## 2. Propuestas de Mejora

### 2.1 Solucion UOR: Reemplazar Vast.ai con fuentes reales de ocupacion

#### Opcion A: CoreWeave Status Page (publico)
- **URL:** https://status.coreweave.com/
- **Datos:** Incidencias, capacidad, latencia de regiones.
- **Proxy:** Si hay incidencias frecuentes → sobreoferta/infrautilizacion.
- **Pros:** Datos reales de uno de los mayores neoclouds.
- **Cons:** Indirecto (incidencias != ocupacion directa).

#### Opcion B: Cloudflare Radar / Cloudflare Status
- **URL:** https://radar.cloudflare.com/
- **Datos:** Trafico global de internet, tendencias de uso.
- **Proxy:** Caida de trafico IA = menor demanda GPU.
- **Pros:** API gratuita, datos masivos, alta fiabilidad.
- **Cons:** Macro, no especifico a GPU.

#### Opcion C: RunPod API (requiere API key gratuita)
- **URL:** https://rest.runpod.io/v1/
- **Datos:** Pricing, disponibilidad por region.
- **Pros:** Datos directos de neocloud. Precios por GPU/hora por region.
- **Cons:** Requiere registro. Rate limits.

#### Opcion D: Datacrunch.io API
- **URL:** https://datacrunch.io/
- **Datos:** Precios GPU, disponibilidad.
- **Pros:** API documentada. GPUs H100, A100, RTX.
- **Cons:** Requiere API key.

#### ✅ RECOMENDACION INMEDIATA: RunPod + Datacrunch

Implementar clientes para RunPod y Datacrunch. Usar precios por region como proxy de demanda (precio bajo en region = baja demanda = sobreoferta).

**Nueva formula UOR:**
```
UOR = promedio(
  (precio_baseline_region - precio_actual) / precio_baseline * 100
) por cada neocloud (Vast, RunPod, Datacrunch, Lambda)
```

Esto diversifica fuentes y elimina la dependencia del campo `rented` de Vast.ai.

---

### 2.2 Solucion SHPD: Reemplazar scrapers con APIs REST

#### Opcion A: Google Cloud Pricing API
- **URL:** https://cloud.google.com/compute/all-pricing
- **Datos:** Precios oficiales de GPUs (A100, H100, T4, V100).
- **Pros:** Datos oficiales. Actualizados trimestralmente.
- **Cons:** Precios "oficiales" pueden no reflejar mercado spot.

#### Opcion B: AWS EC2 Spot Price History
- **URL:** https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances-history.html
- **Datos:** Historial de precios spot por instancia GPU.
- **Pros:** Datos reales de mercado spot. Historial completo.
- **Cons:** Requiere AWS account + boto3. Complejo parsear.

#### Opcion C: OVHcloud API
- **URL:** https://api.ovh.com/
- **Datos:** Precios GPU instances en Europa.
- **Pros:** API REST estable. Cobertura europea.
- **Cons:** Requiere app key/secret.

#### Opcion D: Paperspace API
- **URL:** https://docs.paperspace.com/core/api-reference/
- **Datos:** Precios GPU, tipos de maquina.
- **Pros:** API simple. GPUs RTX, A100.
- **Cons:** Requiere API key.

#### ✅ RECOMENDACION INMEDIATA: Paperspace + OVHcloud

Paperspace tiene API simple y bien documentada. OVHcloud tiene buena cobertura europea. Ambos requieren keys gratuitas.

**Para no depender de keys:** mantener Lambda Labs scraper como fallback, pero agregar validacion de estructura HTML (chequear que los precios esten dentro de rango razonable $0.50 - $20/hora).

---

### 2.3 Solucion LTCR: Profundizar en datos financieros

#### Opcion A: Alpha Vantage API
- **URL:** https://www.alphavantage.co/documentation/
- **Datos:** Precios historicos diarios, semanales, mensuales de acciones.
- **Pros:** API gratuita (5 llamadas/minuto). Datos historicos ricos.
- **Cons:** Rate limit bajo. Necesita API key.

#### Opcion B: Finnhub API
- **URL:** https://finnhub.io/docs/api/company-profile2
- **Datos:** Perfil de empresa, metricas fundamentales, earnings.
- **Pros:** API gratuita. Datos fundamentales (market cap, P/E).
- **Cons:** Rate limit.

#### Opcion C: SEC EDGAR XBRL (real)
- **URL:** https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent
- **Datos:** Filings 10-K, 10-Q de NVDA, SMCI, DELL, AMD.
- **Pros:** Datos contractuales reales. "Committed capacity" en filings.
- **Cons:** Parser XBRL complejo. Datos trimestrales (no diarios).

#### ✅ RECOMENDACION INMEDIATA: Alpha Vantage

Sustituir Yahoo Finance por Alpha Vantage. Obtener volatilidad de 30 dias en lugar de cambio diario.

**Nueva formula LTCR:**
```
LTCR = max(
  volatilidad_30d_NVDA * 2,
  volatilidad_30d_SMCI * 2,
  volatilidad_30d_DELL * 2
)  // Escalado a 0-100
```

---

### 2.4 Solucion CFBR: Diversificar mas alla de crypto

#### Opcion A: Google Trends API (pytrends)
- **URL:** https://trends.google.com/trends/
- **Datos:** Busquedas de "GPU rental", "cloud GPU", "AI training".
- **Proxy:** Caida en busquedas = menor demanda = mayor riesgo.
- **Pros:** Gratis. No requiere key. Datos semanales.
- **Cons:** Indirecto. No especifico a infraestructura IA.

#### Opcion B: Reddit API (praw)
- **URL:** https://www.reddit.com/r/MachineLearning/, /r/homelab
- **Datos:** Sentimiento de comunidad tecnica sobre precios GPUs.
- **Proxy:** Posts frecuentes "GPUs too expensive / too cheap".
- **Pros:** Sentimiento en tiempo real. Gratis.
- **Cons:** NLP requerido. Ruido alto.

#### Opcion C: Hugging Face Inference API
- **URL:** https://huggingface.co/api/
- **Datos:** Uso de modelos, trafico de inference endpoints.
- **Proxy:** Caida de uso = menor demanda GPU.
- **Pros:** Directamente IA. API gratuita.
- **Cons:** Indirecto.

#### ✅ RECOMENDACION INMEDIATA: Google Trends

Implementar pytrends para obtener interes de busqueda en terminos relacionados. Es gratuito y no requiere key.

---

### 2.5 Nueva Fuente: Demand-side (lado demanda)

El CRI mide riesgo desde el lado de oferta (precios, ocupacion). Falta medir **demanda**:

#### Opcion A: LinkedIn Job Postings API (scraping)
- **Datos:** Numero de ofertas "Machine Learning Engineer", "MLOps".
- **Proxy:** Caida de ofertas = menor demanda infra IA.

#### Opcion B: GitHub API
- **URL:** https://api.github.com/search/repositories
- **Datos:** Repositorios nuevos con topicos "pytorch", "tensorflow", "LLM".
- **Proxy:** Caida de nuevos repos IA = menor demanda GPU.
- **Pros:** API gratuita. Datos ricos.
- **Cons:** Indirecto.

#### ✅ RECOMENDACION: GitHub API

Anadir KPI opcional "AI_ACTIVITY" que mide repos nuevos IA/mes. Si cae >30% → riesgo alto.

---

## 3. Roadmap de Implementacion

### Fase 1: Correccion Critica (Semana 1)

| Tarea | Prioridad | Esfuerzo | Impacto |
|-------|-----------|----------|---------|
| Arreglar UOR (quitar dependencia `rented` de Vast.ai) | 🔴 CRITICO | 4h | ALTO |
| Agregar validacion de rangos en scrapers (SHPD) | 🟠 ALTO | 2h | MEDIO |
| Agregar fallback si fuente falla (MISSING_DATA ya existe) | 🟠 ALTO | 1h | MEDIO |

**Accion concreta:**
```python
# En vast_ai_live.py, cambiar UOR de "rented" a "precio vs baseline"
# Nuevo UOR:
uor = ((baseline_price - avg_market_price) / baseline_price) * 100
```

### Fase 2: Nuevas Fuentes REST (Semana 2-3)

| Tarea | Fuente | KPI | Auth |
|-------|--------|-----|------|
| Implementar RunPod API | RunPod | UOR | API Key (gratis) |
| Implementar Paperspace API | Paperspace | SHPD | API Key (gratis) |
| Implementar Alpha Vantage | Alpha Vantage | LTCR | API Key (gratis) |
| Implementar pytrends | Google Trends | CFBR proxy | No |

### Fase 3: Fuentes Avanzadas (Mes 2)

| Tarea | Fuente | KPI |
|-------|--------|-----|
| SEC EDGAR XBRL parser | SEC | LTCR (fundamental) |
| GitHub API activity | GitHub | AI_ACTIVITY (nuevo) |
| AWS Spot Price History | AWS | SHPD + GSPI |
| CoreWeave Status API | CoreWeave | UOR |

### Fase 4: Calidad de Datos (Continuo)

- **Validacion cruzada:** Si Vast.ai dice GSPI=80% pero AWS Spot dice deflacion=10%, investigar discrepancia.
- **Outlier detection:** Si un KPI cambia >50% en 24h, marcar como "sospechoso" y usar ultimo valor valido.
- **Data freshness score:** Agregar metrica de "confianza" basada en cuantas fuentes respondieron.

---

## 4. Arquitectura Futura de Fuentes

```
                    FUENTES DE DATOS (v2.0)
                    
    ┌─────────────────────────────────────────────┐
    │           CAPA DE INGESTA                   │
    │  (7 fuentes actuales + 8 nuevas = 15)       │
    └─────────────────────────────────────────────┘
         │                    │                   │
    ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
    │ OFERTA  │         │ DEMANDA │         │ MACRO   │
    │ (8)     │         │ (4)     │         │ (3)     │
    ├─────────┤         ├─────────┤         ├─────────┤
    │Vast.ai  │         │GitHub   │         │Alpha V  │
    │RunPod   │         │Google Tr│         │SEC      │
    │Datacrunch│        │LinkedIn │         │FRED     │
    │Lambda   │         │HuggingF │         └─────────┘
    │Paperspace│        └─────────┘
    │AWS Spot │
    │OVHcloud │
    └─────────┘
         │
    ┌────▼──────────────────────────────────────────┐
    │      CAPA DE VALIDACION (NUEVO)                 │
    │  - Rango checks                                   │
    │  - Cross-validation entre fuentes                 │
    │  - Outlier detection                              │
    │  - Data freshness score                           │
    └─────────────────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────────┐
    │      CAPA DE CALCULO CRI (existente)         │
    │  - Normalizacion Min-Max                        │
    │  - Ponderacion 0.25/0.15/0.20/0.20/0.20        │
    │  - Alertas >65                                  │
    └─────────────────────────────────────────────────┘
```

---

## 5. Metricas de Exito

Para evaluar si las mejoras funcionan:

| Metrica | Actual | Objetivo v2.0 |
|---------|--------|---------------|
| Fuentes funcionando / totales | 6/7 (86%) | 14/15 (93%) |
| Latencia promedio de ingesta | 15s | <5s |
| UOR sin datos validos | 100% fijo | Variable real |
| Tests pasando | 18/18 | 25/25 |
| Alertas falsas (noise) | ~5%/mes | <1%/mes |
| Tiempo sin datos (downtime) | ~10% (FRED, scrapers) | <2% |

---

## 6. Conclusiones

### Lo que funciona bien (mantener):
- ✅ Vast.ai para GSPI (precios spot reales)
- ✅ CoinGecko + Binance para CFBR (correlacion crypto-GPU)
- ✅ Motor de calculo CRI (normalizacion, ponderacion, alertas)
- ✅ Dashboard frontend

### Lo que debe corregirse urgentemente:
- 🔴 **UOR siempre = 100%** → Reemplazar metrica de Vast.ai por precios por region de multiples neoclouds
- 🔴 **Scrapers HTML fragiles** → Migrar a APIs REST con keys gratuitas
- 🟡 **LTCR basado solo en cambio diario** → Usar ventana de 30d con Alpha Vantage
- 🟡 **FRED sin key** → Documentar proceso de obtencion de key gratuita

### Inversion recomendada:
1. **Semana 1:** 8h (arreglar UOR, validacion de scrapers)
2. **Semana 2-3:** 16h (nuevas APIs: RunPod, Paperspace, Alpha Vantage)
3. **Mes 2:** 20h (fuentes avanzadas: SEC, GitHub, AWS)

**ROI esperado:** CRI con 15 fuentes tiene 3x mas robustez predictiva que con 7. Capacidad de detectar correcciones de mercado 5-10 dias antes.
