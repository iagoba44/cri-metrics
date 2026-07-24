import requests, json

r = requests.post('http://localhost:8000/api/v1/calculate-cri', timeout=30)
data = r.json()['data']
print(f"CRI Score: {data['cri_score']}")
print(f"Risk Zone: {data['risk_zone']}")
print(f"Alerts: {data['alerts_triggered']}")
print('KPIs:')
for k,v in data['component_scores'].items():
    print(f"  {k}: raw={v['raw_value']:.2f} score={v['normalized_score']:.2f}")
