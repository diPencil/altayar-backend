"""
Comprehensive System Check Script
Tests backend, database, APIs, and services
"""
import sys
import os
import traceback
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check environment variables and configuration"""
    print("\n" + "="*60)
    print("1. ENVIRONMENT CHECK")
    print("="*60)
    
    issues = []
    
    # Check .env file
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        issues.append("[ERROR] .env file not found")
    else:
        print("[OK] .env file exists")
    
    # Try to load settings
    try:
        from config.settings import settings
        print("[OK] Settings loaded successfully")
        
        # Check required settings
        required_settings = [
            'JWT_SECRET_KEY',
            'SECRET_KEY',
            'FAWATERK_API_KEY',
            'FAWATERK_VENDOR_KEY',
            'DATABASE_URL'
        ]
        
        for setting in required_settings:
            try:
                value = getattr(settings, setting)
                if not value or value == "":
                    issues.append(f"[ERROR] {setting} is empty")
                else:
                    print(f"[OK] {setting} is set")
            except AttributeError:
                issues.append(f"[ERROR] {setting} is missing")
        
        print(f"[OK] Database URL: {settings.DATABASE_URL}")
        print(f"[OK] API Prefix: {settings.API_V1_PREFIX}")
        print(f"[OK] Debug Mode: {settings.DEBUG}")
        
    except Exception as e:
        issues.append(f"[ERROR] Failed to load settings: {e}")
        print(f"[ERROR] Error: {traceback.format_exc()}")
    
    return issues

def check_database():
    """Check database connectivity"""
    print("\n" + "="*60)
    print("2. DATABASE CHECK")
    print("="*60)
    
    issues = []
    
    try:
        from database.base import engine, Base, SessionLocal
        print("[OK] Database module imported successfully")
        
        # Test connection
        try:
            with engine.connect() as conn:
                print("[OK] Database connection successful")
        except Exception as e:
            issues.append(f"[ERROR] Database connection failed: {e}")
            print(f"[ERROR] Error: {traceback.format_exc()}")
        
        # Check if tables can be created
        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
            print("[OK] Database tables verified")
        except Exception as e:
            issues.append(f"[ERROR] Database table creation failed: {e}")
            print(f"[ERROR] Error: {traceback.format_exc()}")
        
    except Exception as e:
        issues.append(f"[ERROR] Database module import failed: {e}")
        print(f"[ERROR] Error: {traceback.format_exc()}")
    
    return issues

def check_routes():
    """Check all route modules"""
    print("\n" + "="*60)
    print("3. ROUTES CHECK")
    print("="*60)
    
    issues = []
    routes_to_check = [
        ('modules.auth.routes', 'auth'),
        ('modules.referrals.routes', 'referrals'),
        ('modules.memberships.routes', 'memberships'),
        ('modules.points.routes', 'points'),
        ('modules.wallet.routes', 'wallet'),
        ('modules.cashback.routes', 'cashback'),
        ('modules.offers.routes', 'offers'),
        ('modules.bookings.routes', 'bookings'),
        ('modules.chat.routes', 'chat'),
        ('modules.payments.routes', 'payments'),
        ('modules.orders.routes', 'orders'),
        ('modules.invoices.routes', 'invoices'),
        ('modules.admin.routes', 'admin'),
        ('modules.reels.routes', 'reels'),
        ('modules.notifications.routes', 'notifications'),
    ]
    
    for module_path, name in routes_to_check:
        try:
            module = __import__(module_path, fromlist=['router'])
            if hasattr(module, 'router'):
                print(f"[OK] {name} routes loaded")
            else:
                issues.append(f"[ERROR] {name} routes: router not found")
                print(f"[ERROR] {name} routes: router not found")
        except Exception as e:
            issues.append(f"[ERROR] {name} routes failed: {e}")
            print(f"[ERROR] {name} routes failed: {str(e)[:100]}")
    
    return issues

def check_dependencies():
    """Check critical dependencies"""
    print("\n" + "="*60)
    print("4. DEPENDENCIES CHECK")
    print("="*60)
    
    issues = []
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('sqlalchemy', 'sqlalchemy'),
        ('pydantic', 'pydantic'),
        ('pydantic_settings', 'pydantic_settings'),
        ('python-jose', 'jose'),
        ('passlib', 'passlib'),
        ('bcrypt', 'bcrypt'),
        ('python-dotenv', 'dotenv'),
    ]
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"[OK] {package_name} installed")
        except ImportError:
            issues.append(f"[ERROR] {package_name} not installed")
            print(f"[ERROR] {package_name} not installed")
    
    return issues

def check_server_startup():
    """Check if server can start"""
    print("\n" + "="*60)
    print("5. SERVER STARTUP CHECK")
    print("="*60)
    
    issues = []
    
    try:
        from server import app
        print("[OK] Server app created successfully")
        
        # Check if all routers are included
        routes_count = len(app.routes)
        print(f"[OK] Total routes registered: {routes_count}")
        
        if routes_count < 10:
            issues.append(f"[WARNING] Low route count ({routes_count}), some routes may be missing")
        
    except Exception as e:
        issues.append(f"[ERROR] Server startup failed: {e}")
        print(f"[ERROR] Error: {traceback.format_exc()}")
    
    return issues

def check_shared_modules():
    """Check shared modules"""
    print("\n" + "="*60)
    print("6. SHARED MODULES CHECK")
    print("="*60)
    
    issues = []
    
    shared_modules = [
        'shared.dependencies',
        'shared.exceptions',
        'shared.schemas',
        'shared.utils',
    ]
    
    for module_path in shared_modules:
        try:
            __import__(module_path)
            print(f"[OK] {module_path} imported")
        except Exception as e:
            issues.append(f"[ERROR] {module_path} failed: {e}")
            print(f"[ERROR] {module_path} failed: {str(e)[:100]}")
    
    return issues

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("SYSTEM CHECK - AltayarVIP Backend")
    print("="*60)
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_environment())
    all_issues.extend(check_dependencies())
    all_issues.extend(check_database())
    all_issues.extend(check_shared_modules())
    all_issues.extend(check_routes())
    all_issues.extend(check_server_startup())
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if all_issues:
        print(f"\n[ERROR] Found {len(all_issues)} issue(s):")
        for issue in all_issues:
            print(f"  {issue}")
        return 1
    else:
        print("\n[OK] All checks passed! System is ready.")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
