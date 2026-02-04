import urllib.request
import urllib.error
import sys

BASE_URL = "http://localhost:8082/api"

def check_endpoint(url, method="GET"):
    print(f"Checking {method} {url}...")
    try:
        req = urllib.request.Request(url, method=method)
        if method == "OPTIONS":
            req.add_header("Origin", "http://localhost:8081")
            req.add_header("Access-Control-Request-Method", "POST")
        
        with urllib.request.urlopen(req) as response:
            print(f"✅ Status: {response.status}")
            if method == "OPTIONS":
                cors_origin = response.getheader("Access-Control-Allow-Origin")
                print(f"CORS Origin: {cors_origin}")
                if cors_origin == "*" or cors_origin == "http://localhost:8081":
                    print("✅ CORS Headers present")
                else:
                    print("❌ CORS Headers MISSING or Incorrect")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} {e.reason}")
        if e.code == 404:
            print("!!! Route conflict likely still exists if this is /categories !!!")
        return False
    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason}")
        return False

print("=== Verifying Fixes ===")

# 1. Check Categories Endpoint (Was 404 before fix)
print("\n1. Verifying /offers/categories fixes 'Offer not found' (404)...")
if check_endpoint(f"{BASE_URL}/offers/categories"):
    print("✅ /offers/categories is reachable! Route ordering fixed.")
else:
    print("❌ /offers/categories failed.")

# 2. Check CORS on /offers
print("\n2. Verifying CORS on /offers...")
check_endpoint(f"{BASE_URL}/offers", method="OPTIONS")

print("\n=== Done ===")
