import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get("https://gora.ru.net/", headers=headers, verify=False)
    print(f"Status: {r.status_code}")
    print(r.text[:2000]) # First 2000 chars
except Exception as e:
    print(f"Error: {e}")
