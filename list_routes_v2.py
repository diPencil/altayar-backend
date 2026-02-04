import sys
import os
import logging

# Configure logging to capture output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_routes")

# Add the current directory to sys.path
sys.path.append(os.getcwd())

print("--- STARTING APP LOAD ---")
try:
    from server import app
    print("--- APP LOADED ---")
    
    print(f"Total routes in app: {len(app.routes)}")
    
    admin_routes = [r for r in app.routes if hasattr(r, "path") and "/admin" in r.path]
    print(f"Admin-related routes (/admin): {len(admin_routes)}")
    
    for route in admin_routes:
        print(f"{route.methods} {route.path}")
        
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
