import urllib.request
import json
import urllib.error

url = "http://127.0.0.1:8001/api/auth/login"
payload = {
    "identifier": "admin@altayar.com",
    "password": "admin123"
}
data = json.dumps(payload).encode('utf-8')
headers = {
    "Content-Type": "application/json"
}

req = urllib.request.Request(url, data=data, headers=headers)

print(f"Testing {url}...")
try:
    with urllib.request.urlopen(req) as response:
        print(f"✅ Success! Status: {response.getcode()}")
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"❌ HTTP Error: {e.code}")
    print(e.read().decode())
except urllib.error.URLError as e:
    print(f"❌ Connection Failed: {e.reason}")
