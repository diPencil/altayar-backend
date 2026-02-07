"""
AltayarVIP Backend Server
FastAPI application entry point
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Import settings
from config.settings import settings

# Import database
from database.base import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting AltayarVIP Backend Server...")
    logger.info(f"📊 Database: {settings.DATABASE_URL}")
    logger.info(f"🔧 Debug Mode: {settings.DEBUG}")
    logger.info(f"🌐 APP_BASE_URL: {getattr(settings, 'APP_BASE_URL', '')}")
    logger.info(f"💳 Payment redirects: success={getattr(settings, 'PAYMENT_SUCCESS_URL', '')}, fail={getattr(settings, 'PAYMENT_FAIL_URL', '')}")
    logger.info(f"💳 Fawaterk default payment method: {getattr(settings, 'FAWATERK_DEFAULT_PAYMENT_METHOD', 2)} (2=Fawry)")
    
    # Create all tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down AltayarVIP Backend Server...")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS Middleware - Allow all origins in debug mode
# For credentials support, we need to specify origins explicitly (can't use "*" with credentials)
dev_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8080",
    "http://localhost:8081",  # Expo dev server (common port)
    "http://localhost:8082",  # Backend port (for testing)
    "http://localhost:19000",
    "http://localhost:19001",
    "http://localhost:19006",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",  # Expo dev server (common port)
    "http://127.0.0.1:8082",  # Backend port (for testing)
    "http://127.0.0.1:19000",
    "http://127.0.0.1:19001",
    "http://127.0.0.1:19006",
    # Expo Web development server (default ports)
    "http://localhost:19000",  # Expo Web default
    "http://localhost:19006",  # Expo Web tunnel
    "http://192.168.1.17:8081",  # Common local network IP
    "http://192.168.1.17:8082",  # Backend on network
    "http://192.168.1.17:19006",  # Expo Web on network
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=dev_origins if settings.DEBUG else settings.cors_origins,
    allow_credentials=True,  # Allow credentials for auth headers
    allow_methods=["*"],
    allow_headers=["*"],  # This includes Authorization, Content-Type, etc.
    expose_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Import and include routers
try:
    # Auth routes
    try:
        from modules.auth.routes import router as auth_router
        app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
        logger.info("✅ Auth routes loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load auth routes: {e}")

    # Referral routes
    try:
        from modules.referrals.routes import router as referrals_router
        app.include_router(referrals_router, prefix=f"{settings.API_V1_PREFIX}/referrals", tags=["Referrals"])
        logger.info("✅ Referrals routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Referrals routes failed: {e}")

    # User routes
    # Note: User management is handled through Admin routes
    # try:
    #     from modules.users.routes import router as users_router
    #     app.include_router(users_router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
    #     logger.info("✅ User routes loaded successfully")
    # except Exception as e:
    #     logger.error(f"❌ Failed to load user routes: {e}")

    # Membership routes
    try:
        from modules.memberships.routes import router as memberships_router
        app.include_router(memberships_router, prefix=f"{settings.API_V1_PREFIX}/memberships", tags=["Memberships"])
        logger.info("✅ Membership routes loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load membership routes: {e}")

    # Points routes
    try:
        from modules.points.routes import router as points_router
        app.include_router(points_router, prefix=f"{settings.API_V1_PREFIX}/points", tags=["Points"])
        logger.info("✅ Points routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Points routes failed: {e}")

    # Games routes - Removed
    # try:
    #     from modules.games.routes import router as games_router
    #     app.include_router(games_router, prefix=f"{settings.API_V1_PREFIX}/games", tags=["Games"])
    #     logger.info("✅ Games routes loaded successfully")
    # except Exception as e:
    #     logger.warning(f"⚠️ Games routes failed: {e}")

    # Wallet routes
    try:
        from modules.wallet.routes import router as wallet_router
        app.include_router(wallet_router, prefix=f"{settings.API_V1_PREFIX}/wallet", tags=["Wallet"])
        logger.info("✅ Wallet routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Wallet routes failed: {e}")

    # Club Gifts routes (formerly Cashback)
    try:
        from modules.cashback.routes import router as cashback_router
        app.include_router(cashback_router, prefix=f"{settings.API_V1_PREFIX}/cashback", tags=["Club Gifts"])
        logger.info("✅ Club Gifts routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Club Gifts routes failed: {e}")

    # Offers routes
    try:
        from modules.offers.routes import router as offers_router
        app.include_router(offers_router, prefix=f"{settings.API_V1_PREFIX}/offers", tags=["Offers"])
        logger.info("✅ Offers routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Offers routes failed: {e}")

    # Bookings routes
    try:
        from modules.bookings.routes import router as bookings_router
        app.include_router(bookings_router, prefix=f"{settings.API_V1_PREFIX}/bookings", tags=["Bookings"])
        logger.info("✅ Bookings routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Bookings routes failed: {e}")

    # Chat routes
    try:
        from modules.chat.routes import router as chat_router
        app.include_router(chat_router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["Chat"])
        logger.info("✅ Chat routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Chat routes failed: {e}")

    # Payments routes
    try:
        from modules.payments.routes import router as payments_router
        app.include_router(payments_router, prefix=f"{settings.API_V1_PREFIX}/payments", tags=["Payments"])
        logger.info("✅ Payments routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Payments routes failed: {e}")

    # Orders routes
    try:
        from modules.orders.routes import router as orders_router
        app.include_router(orders_router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["Orders"])
        logger.info("✅ Orders routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Orders routes failed: {e}")

    # Invoices routes
    try:
        from modules.invoices.routes import router as invoices_router
        app.include_router(invoices_router, prefix=f"{settings.API_V1_PREFIX}/invoices", tags=["Invoices"])
        logger.info("✅ Invoices routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Invoices routes failed: {e}")

    # Admin routes
    try:
        from modules.admin.routes import router as admin_router
        app.include_router(admin_router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])
        logger.info("✅ Admin routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Admin routes failed: {e}")

    # Reels routes
    try:
        from modules.reels.routes import router as reels_router
        app.include_router(reels_router, prefix=f"{settings.API_V1_PREFIX}/reels", tags=["Reels"])
        logger.info("✅ Reels routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Reels routes failed: {e}")
    
    # Tier Posts routes
    try:
        from modules.tier_posts.routes import router as tier_posts_router
        app.include_router(tier_posts_router, prefix=f"{settings.API_V1_PREFIX}/tier-posts", tags=["Tier Posts"])
        logger.info("✅ Tier Posts routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Tier Posts routes failed: {e}")
    
    # Notifications routes
    try:
        from modules.notifications.routes import router as notifications_router
        app.include_router(notifications_router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["Notifications"])
        logger.info("✅ Notifications routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Notifications routes failed: {e}")
    
    # Employee routes
    try:
        from modules.employee.routes import router as employee_router
        app.include_router(employee_router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Employee"])
        logger.info("✅ Employee routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Employee routes failed: {e}")

    # Settings routes
    try:
        from modules.settings.routes import router as settings_router
        app.include_router(settings_router, prefix=f"{settings.API_V1_PREFIX}/settings", tags=["Settings"])
        logger.info("✅ Settings routes loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Settings routes failed: {e}")


except Exception as e:
    logger.warning(f"⚠️ Some routes failed to load: {e}")

# Global exception handler with proper CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions with proper CORS headers"""
    from fastapi import HTTPException
    
    # Get origin from request to set proper CORS headers
    origin = request.headers.get("origin", "")
    headers = {}
    
    # Check if origin is allowed
    allowed_origins = dev_origins if settings.DEBUG else settings.cors_origins
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"
    
    # Handle HTTPException (401, 403, 404, etc.)
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers
        )
    
    # For other exceptions, log and return generic error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8082,
        reload=settings.DEBUG
    )
