import requests

r = requests.get('http://127.0.0.1:8000/api/v1/sources')
print(f"Status: {r.status_code}")
print(f"Headers: {r.headers.get('content-type')}")
print(f"Text: {r.text[:500]}")
