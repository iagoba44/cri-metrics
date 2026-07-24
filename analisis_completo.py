import requests, json, time
from datetime import datetime

BASE = 'http://127.0.0.1:8000'

print("=" * 70)
print("CRI METRICS - ANALISIS COMPLETO EN LOCAL")
print("=" * 70)
print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
print(f"Servidor: {BASE}")
print("=" * 70)

# 1. Health
print("\n[1] HEALTH CHECK")
r = requests.get(f'{BASE}/api/v1/health')
print(f"  Status: {r.json()['status']}")
print(f"  Version: {r.json()['version']}")

# 2. Ingesta real
print("\n[2] INGESTA DESDE FUENTES REALES (esto puede tardar 10-20s)...")
t0 = time.time()
r = requests.post(f'{BASE}/api/v1/run-ingestion?use_real=true', timeout=120)
ingesta = r.json()
t1 = time.time()
print(f"  Insertados: {ingesta['inserted']} registros")
print(f"  Tiempo: {t1-t0:.1f}s")
print(f"  Mensaje: {ingesta['message']}")

# 3. Calcular CRI
print("\n[3] CALCULO CRI")
r = requests.post(f'{BASE}/api/v1/calculate-cri', timeout=30)
cri = r.json()['data']
print(f"  CRI Score: {cri['cri_score']}")
print(f"  Risk Zone: {cri['risk_zone']}")
print(f"  Alerts: {cri['alerts_triggered']}")
print(f"  Timestamp: {cri['timestamp']}")

# 4. Desglose KPIs
print("\n[4] DESGLOSE POR KPI")
print(f"  {'KPI':6s} | {'Raw':>8s} | {'Score':>6s} | {'Weight':>6s} | {'Contrib':>8s} | {'Fresh':>6s} | {'Source':20s}")
print(f"  {'-'*78}")
total = 0
for kpi, details in cri['component_scores'].items():
    contrib = details['normalized_score'] * details['weight']
    total += contrib
    print(f"  {kpi:6s} | {details['raw_value']:8.2f} | {details['normalized_score']:6.2f} | "
          f"{details['weight']:6.2f} | {contrib:8.2f} | {details.get('freshness','?'):6s} | ")
print(f"  {'-'*78}")
print(f"  {'TOTAL':6s} | {'':8s} | {'':6s} | {'':6s} | {total:8.2f} |")

# 5. Estado de fuentes
print("\n[5] ESTADO DE FUENTES (TIEMPO REAL)")
r = requests.get(f'{BASE}/api/v1/sources')
src = r.json()
print(f"  Activas: {src['active_kpis']}/{src['total_kpis']}")
print(f"  Stale: {src['stale_kpis']}")
print(f"  Offline: {src['offline_kpis']}")
print(f"  Server time: {src['timestamp']}")
print()
for s in src['sources']:
    d = s['delta_seconds']
    d_str = f'{d:.0f}s' if d < 60 else f'{d/60:.1f}m' if d < 3600 else f'{d/3600:.1f}h'
    status_emoji = 'ACTIVE' if s['status']=='ACTIVE' else 'STALE' if s['status']=='STALE' else 'OFF'
    print(f"  {s['kpi']:6s} | {status_emoji:8s} | raw={s['raw_value']:6.2f} | delta={d_str:>6s} | {s['data_source']:20s} | {s['freshness']}")

# 6. Explicaciones
print("\n[6] EXPLICACIONES KPI (resumen)")
r = requests.get(f'{BASE}/api/v1/explanations')
exp = r.json()
for kpi_code, info in list(exp['explanations'].items())[:6]:
    if kpi_code == 'cri_score':
        print(f"  CRI: {info['name']}")
        print(f"       Formula: {info['formula']}")
    else:
        print(f"  {kpi_code}: {info['name']}")
        print(f"       Fuente: {info.get('source', info.get('sources','N/A'))}")
        print(f"       Peso: {info['weight']}")

# 7. URLs
print("\n[7] URLs ACCESIBLES")
print(f"  Dashboard:  {BASE}/static/index.html")
print(f"  Health:     {BASE}/api/v1/health")
print(f"  Sources:    {BASE}/api/v1/sources")
print(f"  CRI:        {BASE}/api/v1/latest-cri")
print(f"  Explanations: {BASE}/api/v1/explanations")

print("\n" + "=" * 70)
print("ANALISIS LISTO - Abre el dashboard en tu navegador:")
print(f"  {BASE}/static/index.html")
print("=" * 70)
