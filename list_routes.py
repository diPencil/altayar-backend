import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

try:
    from server import app
    print("FastAPI app loaded successfully.")
    
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"{route.methods} {route.path}")
except Exception as e:
    print(f"Error loading app: {e}")
    import traceback
    traceback.print_exc()
