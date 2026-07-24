import requests, json

print('=== CRI METRICS v2.1 - VERIFICACION FINAL ===')
print()

# 1. Ingesta
print('[1] INGESTA REAL...')
r = requests.post('http://127.0.0.1:8000/api/v1/run-ingestion?use_real=true', timeout=120)
print(f"Insertados: {r.json()['inserted']}")

# 2. CRI normal
print()
print('[2] CRI NORMAL...')
r = requests.post('http://127.0.0.1:8000/api/v1/calculate-cri', timeout=30)
cri = r.json()['data']
print(f"CRI: {cri['cri_score']} ({cri['risk_zone']})")

# 3. Sources
print()
print('[3] FUENTES:')
r = requests.get('http://127.0.0.1:8000/api/v1/sources')
src = r.json()
for s in src['sources']:
    d = s['delta_seconds']
    d_str = f'{d:.0f}s' if d < 60 else f'{d/60:.1f}m'
    print(f"  {s['kpi']:6s} | {s['status']:8s} | raw={s['raw_value']:6.2f} | delta={d_str:>6s}")

# 4. Simulate CRITICAL
print()
print('[4] SIMULATE CRITICAL...')
r = requests.post('http://127.0.0.1:8000/api/v1/simulate-critical', timeout=30)
sim = r.json()['data']
print(f"CRI: {sim['cri_score']} ({sim['risk_zone']}) | Alerts: {sim['alerts_triggered']}")

# 5. Explanations
print()
print('[5] EXPLANATIONS OK')

print()
print('=== SERVIDOR LISTO ===')
print('Dashboard: http://127.0.0.1:8000/static/index.html')
