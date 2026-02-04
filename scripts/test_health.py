import urllib.request
import urllib.error

url = "http://127.0.0.1:8001/health"

try:
    print(f"Testing {url}...")
    with urllib.request.urlopen(url) as response:
        print(f"Status Code: {response.getcode()}")
        print(f"Response: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")
except urllib.error.URLError as e:
    print(f"Connection Failed: {e.reason}")
except Exception as e:
    print(f"Error: {e}")
