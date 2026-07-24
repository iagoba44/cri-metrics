import requests, json

print('=== [2] CALCULAR CRI ===')
r = requests.post('http://127.0.0.1:8000/api/v1/calculate-cri', timeout=30)
data = r.json()['data']
print(f"CRI Score: {data['cri_score']}")
print(f"Risk Zone: {data['risk_zone']}")
print(f"Alerts: {data['alerts_triggered']}")
print('KPIs:')
for k,v in data['component_scores'].items():
    print(f"  {k}: raw={v['raw_value']:.2f} score={v['normalized_score']:.2f} freshness={v.get('freshness','?')}")
print()

print('=== [3] FUENTES EN TIEMPO REAL ===')
r = requests.get('http://127.0.0.1:8000/api/v1/sources', timeout=30)
src = r.json()
print(f"Activas: {src['active_kpis']}/{src['total_kpis']}")
for s in src['sources']:
    delta = s['delta_seconds']
    delta_str = f'{delta:.0f}s' if delta < 60 else f'{delta/60:.1f}m' if delta < 3600 else f'{delta/3600:.1f}h'
    print(f"  {s['kpi']:6s} | {s['status']:8s} | raw={s['raw_value']:.2f} | delta={delta_str} | source={s['data_source']}")
print()

print('=== [4] EXPLICACIONES KPI ===')
r = requests.get('http://127.0.0.1:8000/api/v1/explanations', timeout=30)
exp = r.json()
for k,v in list(exp['explanations'].items())[:2]:
    print(f"{k}: {v['name']}")
print('... (ver completo en /api/v1/explanations)')
print()

print('=== [5] DASHBOARD URL ===')
print('http://127.0.0.1:8000/static/index.html')
print('http://127.0.0.1:8000/api/v1/health')
print('http://127.0.0.1:8000/api/v1/sources')
print('http://127.0.0.1:8000/api/v1/explanations')
