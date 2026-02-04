import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import app

print("\n=== REGISTERED ROUTES ===")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"{list(route.methods)} {route.path}")
print("=========================\n")
