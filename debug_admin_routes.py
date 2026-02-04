import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

try:
    from modules.admin.routes import router as admin_router
    print(f"Admin router loaded successfully. Total routes: {len(admin_router.routes)}")
    
    for route in admin_router.routes:
        print(f"{route.methods} {route.path}")
        if "attribute-referral" in route.path:
            print(">>> FOUND ATTRIBUTE-REFERRAL ROUTE <<<")
except Exception as e:
    print(f"Error loading admin router: {e}")
    import traceback
    traceback.print_exc()
