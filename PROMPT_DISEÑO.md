# PROMPT PARA APP DE DISEÑO IA
## CRI Metrics Dashboard v2.4 - Rediseño UX/UI

---

## 1. CONTEXTO DEL PRODUCTO

**CRI Metrics** es un sistema de inteligencia de mercado para infraestructura IA (GPUs, data centers, cloud computing). Mide en tiempo real:

- **CRI (Composite Risk Index)**: Índice de riesgo compuesto 0-100 que evalúa 5 KPIs:
  - GSPI (GPU Spot Price Index) - precios GPU
  - SHPD (Server Hardware Price Deflation) - deflación hardware
  - LTCR (Long-Term Contract Ratio) - salud contratos
  - CFBR (Cloud Free-Burn Rate) - capitalización/distress
  - UOR (Underutilization Ratio) - ocupación infraestructura

- **TMI (Temperature Market Index)**: Índice de temperatura del mercado 0-100:
  - Fear & Greed Index (sentimiento crypto)
  - arXiv papers velocity (R&D)
  - Hacker News activity (interés técnico)
  - Hashrate global (infraestructura activa)
  - AI tokens performance (inversión)

- **10 escenarios de simulación**: Mercado normal, escasez GPU, crash crypto, bull run, etc.

El dashboard consulta **10+ APIs externas** en tiempo real (Vast.ai, CoinGecko, Binance, Yahoo Finance, NiceHash, DeFiLlama, etc.) y calcula valores consenso ponderados.

---

## 2. ESTADO ACTUAL DEL DASHBOARD

### URL de desarrollo: http://127.0.0.1:8000/static/index.html
### Tech stack: HTML5 + CSS3 + Vanilla JS + Chart.js 4.4.1

### Pantallas actuales (descripción detallada):

#### HEADER
- Logo + título "CRI Dashboard" + subtítulo
- 4 botones: "Ingesta Real", "Calcular CRI", "Fuentes", "Refresh"

#### MODO BANNER (cambia color según modo)
- Verde "LIVE" = datos reales de 10 APIs
- Rojo "SIMULATION" = escenario predefinido activo

#### PANEL DE ESCENARIOS (10 tarjetas)
- Grid 5x2 de escenarios con icono, nombre, CRI preview, color de zona
- Ej: "Crash Crypto 💥 CRI 79.25 CRITICAL"

#### KPIs PRINCIPALES (3 cards en grid)
1. **CRI Score Actual** - número grande 3rem + badge de zona (LOW/MODERATE/CRITICAL)
2. **TMI Score** - número grande + badge (COLD/WARM/HOT)
3. **Historial CRI** - gráfico line Chart.js (mock data estático)

#### KPIs INDIVIDUALES (5 tarjetas)
- GSPI, SHPD, LTCR, CFBR, UOR
- Cada una: nombre, valor normalizado, raw value, peso, contribución, barra de progreso

#### COMPOSICIÓN DEL RIESGO
- Donut chart Chart.js mostrando peso de cada KPI en el CRI

#### FUENTES DE DATOS
- Grid de tarjetas con nombre, descripción, URL, estado (● verde/rojo)
- 10 fuentes listadas

#### PANEL DETALLADO DE FUENTES
- Timestamp exacto, delta en segundos, freshness, data_source

#### COMPONENTES TMI
- 5 barras: Fear & Greed, arXiv, HN, Hashrate, AI Tokens
- Valor, peso, contribución, barra visual

#### EXPLICACIONES
- Guía detallada de qué mide cada KPI
- Fórmulas, baselines, interpretaciones 0%/50%/100%

#### LOG DE OPERACIONES
- Consola estilo terminal con timestamps
- Entries: info (azul), success (verde), error (rojo), warn (naranja)

---

## 3. PROBLEMAS DE UX/UI IDENTIFICADOS

### A. Jerarquía visual confusa
- 3 cards principales (CRI, TMI, Historial) tienen el mismo peso visual
- El historial mock no aporta valor real → debería ser más pequeño o eliminado hasta tener datos reales
- Los 5 KPIs individuales compiten por atención con los scores principales

### B. Densidad de información excesiva
- 10+ secciones en una sola página sin agrupación lógica
- El usuario no sabe dónde mirar primero
- Los botones de control están en el header, lejos de los datos que afectan

### C. Feedback de modo poco visible
- El banner LIVE/SIMULATION es sutil
- No hay indicador visual claro de "estás viendo datos simulados"
- El panel de escenarios aparece/disaparece bruscamente

### D. Charts pobres
- El historial CRI usa datos hardcodeados [45, 48, 52, 50, 55, 55]
- El donut chart es estático y no se actualiza con datos reales
- No hay gráfico de evolución temporal real

### E. Colores y estados
- La paleta GitHub-dark es funcional pero genérica
- No hay diferenciación visual entre "dato real" vs "dato simulado"
- Las barras de progreso son todas grises, sin gradientes ni animaciones

### F. Responsive
- En móvil el grid de 3 columnas se apila mal
- Las tarjetas de escenario son demasiado anchas
- El log de operaciones ocupa demasiado espacio vertical

---

## 4. OBJETIVOS DEL REDISEÑO

### MUST HAVE
1. **Jerarquía clara**: CRI principal → TMI secundario → KPIs detalle → Fuentes metadata
2. **Indicador de modo prominente**: Que sea imposible confundir REAL vs SIMULATION
3. **Charts funcionales**: Historial real desde SQLite, no mock data
4. **Dashboard interactivo**: Tooltips, hover states, transiciones suaves
5. **Diseño responsive**: Móvil-first, tablet, desktop

### SHOULD HAVE
6. **Gauge/Speedometer para CRI**: Visual circular 0-100 con color de zona
7. **Termómetro para TMI**: Visual vertical con gradiente frío→caliente
8. **Alertas visuales**: Cuando CRI > 65 o TMI diverge > 40 puntos del CRI
9. **Heatmap de fuentes**: Grid visual mostrando salud de las 10+ fuentes
10. **Dark/Light mode toggle**

### NICE TO HAVE
11. **Onboarding tour**: Primer uso explica CRI vs TMI
12. **Comparación escenarios**: Side-by-side de 2 escenarios
13. **Export data**: CSV/JSON de los datos actuales
14. **Sound alerts**: Beep cuando entra zona CRITICAL

---

## 5. ESPECIFICACIONES TÉCNICAS

### Constraints
- **Single HTML file** (no React/Vue, solo vanilla JS)
- **Chart.js 4.4.1** ya incluido (CDN)
- **CSS puro** (no Tailwind, no Bootstrap)
- **Responsive** sin frameworks (CSS Grid + Flexbox)
- **Paleta base** (puede ajustarse):
  ```css
  --bg: #0f1115;
  --card: #161b22;
  --border: #30363d;
  --text: #c9d1d9;
  --accent: #58a6ff;
  --danger: #f85149;
  --warning: #d29922;
  --success: #3fb950;
  ```

### APIs disponibles (para integrar)
```
GET /api/v1/health              → {status, timestamp}
GET /api/v1/mode                → {mode, active_scenario, is_simulation}
POST /api/v1/mode               → {mode: "REAL"|"SIMULATION", scenario_id}
GET /api/v1/scenarios           → {scenarios: [...]}
POST /api/v1/simulate-scenario  → {scenario_id} → calcula CRI
POST /api/v1/run-ingestion      → {use_real: true} → ingesta datos
POST /api/v1/calculate-cri      → calcula CRI actual
GET /api/v1/calculate-tmi       → calcula TMI actual
GET /api/v1/latest-cri          → último CRI guardado
GET /api/v1/sources             → estado de todas las fuentes
GET /api/v1/source-weights      → pesos de cada fuente
GET /api/v1/explanations        → documentación KPIs
```

---

## 6. REFERENCIAS DE DISEÑO

### Dashboards de calidad similar
1. **Grafana Cloud** - densidad de métricas, paneles configurables
2. **Datadog** - jerarquía de alertas, colores de estado
3. **CoinMarketCap** - gauges crypto, sparklines
4. **TradingView** - charts técnicos, modo claro/oscuro
5. **Vercel Analytics** - minimalismo, tipografía, espaciado

### Paletas recomendadas (alternativas a GitHub-dark)
- **Opción A**: Mantener GitHub-dark pero añadir glassmorphism y glows
- **Opción B**: Dashboard financiero (blacks profundos #000, acentos neón)
- **Opción C**: NASA/SpaceX style (azules profundos, rojos de alerta, verdes de sistema)

---

## 7. ESTRUCTURA DE PÁGINA PROPUESTA

### NUEVA JERARQUÍA (top to bottom)

```
┌─────────────────────────────────────────┐
│  HEADER: Logo | CRI Dashboard v2.4    │
│  [LIVE ●] Modo Real 10 fuentes activas │ ← Badge prominente
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │   CRI    │  │   TMI    │  │TREND  │ │ ← 3 cards principales
│  │  [GAUGE] │  │[TERMOM]  │  │Spark  │ │   Gauge + Termómetro
│  │  47.94   │  │  51.27   │  │ 24h  │ │   + sparkline 24h
│  │ MODERATE │  │  WARM    │  │      │ │
│  └──────────┘  └──────────┘  └───────┘ │
│                                         │
├─────────────────────────────────────────┤
│  ESCENARIOS (grid 5x2)                  │ ← Solo visible en SIMULATION
│  [Click para cambiar]                   │
├─────────────────────────────────────────┤
│  KPIs DETALLE (5 cards compactas)       │
│  GSPI SHPD LTCR CFBR UOR                │
│  [bars] [vals] [sources]                │
├─────────────────────────────────────────┤
│  COMPOSICIÓN + FUENTES (2 cols)         │
│  [Donut]  [Heatmap 10 fuentes]          │
├─────────────────────────────────────────┤
│  TMI COMPONENTES (5 barras horizontales)  │
│  Fear&Greed | arXiv | HN | Hash | Tokens│
├─────────────────────────────────────────┤
│  EXPLICACIONES (collapsible accordion)  │
│  ▼ Qué mide cada KPI                    │
├─────────────────────────────────────────┤
│  LOG DE OPERACIONES (footer, height:200)│
│  [timestamp] INFO: Ingesta completada...  │
└─────────────────────────────────────────┘
```

---

## 8. ENTREGABLES ESPERADOS

### Opción A: Diseño estático (Figma/Sketch/Framer)
- [ ] Mockup desktop 1920x1080
- [ ] Mockup tablet 768x1024
- [ ] Mockup mobile 375x812
- [ ] Style guide (tipografía, colores, espaciado, componentes)
- [ ] Interacciones/hover states documentados

### Opción B: Código generado (v0.dev, Lovable, Bolt)
- [ ] HTML/CSS/JS completo funcional
- [ ] Integrado con las APIs listadas arriba
- [ ] Responsive implementado
- [ ] Charts funcionales con datos reales

### Opción C: Componentes individuales
- [ ] Gauge circular para CRI (0-100, 3 zonas de color)
- [ ] Termómetro vertical para TMI (0-100, gradiente)
- [ ] Sparkline para historial (mini chart sin ejes)
- [ ] Heatmap de fuentes (10 celdas con color de salud)
- [ ] Card de escenario con icono + preview CRI

---

## 9. CONTEXTO ADICIONAL

### Usuarios objetivo
- **Inversores VCs** en infraestructura IA
- **CTOs** decidiendo compra/leasing de GPUs
- **Analistas** de mercado cloud
- **Mineros** evaluando rentabilidad

### Diferenciador clave
Este NO es un dashboard genérico. Es el **único** sistema que combina:
- Precios spot GPU en tiempo real
- Rentabilidad minera
- Volatilidad crypto
- Acciones de infraestructura IA
- Papers de investigación ML
- Sentimiento del mercado

Todo en un **índice ponderado** con **validación cruzada** entre fuentes.

### Tonos de comunicación
- Profesional pero accesible
- Datos duros, presentación clara
- Alertas sin pánico (información, no sensacionalismo)
- En español (principal) con soporte para inglés futuro

---

## 10. NOTAS PARA EL DISEÑADOR

**NO quiero:**
- ❌ Dashboard genérico de Bootstrap
- ❌ 50 métricas en una pantalla
- ❌ Colores pastel o corporativos aburridos
- ❌ Layout de 2015 con sidebars pesados

**SÍ quiero:**
- ✅ Dark mode por defecto (esto es infraestructura, no Instagram)
- ✅ Animaciones sutiles (pulse en LIVE, transiciones 0.3s)
- ✅ Glassmorphism sutil en cards (bordes brillantes, fondos translúcidos)
- ✅ Tipografía monoespaciada para números (Consolas/Inter/Roboto Mono)
- ✅ Datos que brillan (literally: glow en los números principales)
- ✅ Mobile-first que no se vea vacío en desktop

---

## PROMPT RESUMIDO PARA CHAT

> "Rediseña un dashboard de inteligencia de mercado para infraestructura IA. Mide dos índices principales: CRI (riesgo 0-100) y TMI (temperatura 0-100). Consulta 10+ APIs externas en tiempo real. Modo REAL (datos reales, banner verde) vs SIMULATION (10 escenarios predefinidos, banner rojo). 
>
> Problemas actuales: jerarquía visual confusa, demasiada densidad, charts con mock data, no se distingue bien REAL vs SIMULADO.
>
> Objetivos: (1) Gauge circular para CRI, (2) Termómetro para TMI, (3) Sparkline real 24h, (4) Heatmap de fuentes, (5) Modo prominente, (6) Responsive.
>
> Tech: HTML5 + CSS3 + Chart.js. Single file. Dark mode default.
>
> Referencias: Grafana, Datadog, TradingView, Vercel Analytics.
>
> Genera: mockup desktop + style guide + componente gauge + componente termómetro."

---

**Archivos actuales del proyecto:**
- `static/index.html` (1,054 líneas, dashboard actual)
- `app/api/v1/endpoints.py` (APIs backend)
- Repositorio: `D:\Proyectos\METRICAS CRISS ia\cri_metrics`
