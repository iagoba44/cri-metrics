import requests, traceback, sys

try:
    r = requests.get('http://127.0.0.1:8000/api/v1/sources')
    print(f"Status: {r.status_code}")
    print(f"Text: {r.text}")
    if r.status_code == 200:
        print(f"JSON: {r.json()}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
