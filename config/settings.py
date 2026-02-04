from pydantic_settings import BaseSettings
from typing import List, Optional
import json


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./altayarvip.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Security
    SECRET_KEY: str
    BACKEND_CORS_ORIGINS: str = '["*"]'
    
    @property
    def cors_origins(self) -> List[str]:
        try:
            # Parse JSON string to list
            origins = json.loads(self.BACKEND_CORS_ORIGINS)
            # Add common development origins
            dev_origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:8080",
                "http://localhost:8081",
                "http://localhost:19000",
                "http://localhost:19001",
                "http://localhost:19006",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8081",
                "http://127.0.0.1:19006",
            ]
            
            # If default is "*", replace it with specific origins for credentials support
            if origins == ["*"]:
                return dev_origins
                
            # Otherwise append dev origins to configured ones
            for origin in dev_origins:
                if origin not in origins:
                    origins.append(origin)
                    
            return origins
        except:
            # Fallback to specific origins in development
            return [
                "http://localhost:3000",
                "http://localhost:8081",
                "http://localhost:19006",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8081",
                "http://127.0.0.1:19006"
            ]
    
    # Fawaterk Payment Gateway
    FAWATERK_API_KEY: str
    FAWATERK_VENDOR_KEY: str  # For HMAC SHA256 hash validation
    FAWATERK_PROVIDER_KEY: Optional[str] = None
    FAWATERK_BASE_URL: str = "https://app.fawaterk.com/api/v2"
    FAWATERK_TEST_MODE: bool = True
    
    # Application URLs
    APP_BASE_URL: str = "http://localhost:8082"
    PAYMENT_SUCCESS_URL: str = "app://payment/success"
    PAYMENT_FAIL_URL: str = "app://payment/fail"
    
    # Application
    APP_NAME: str = "AltayarVIP"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = True
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@altayarvip.com"
    EMAILS_FROM_NAME: str = "AltayarVIP"
    
    # Currency & Localization
    DEFAULT_CURRENCY: str = "USD"  # Changed from "EGP" to "USD"
    SUPPORTED_CURRENCIES: str = '["USD","EUR","SAR","EGP"]'
    DEFAULT_CURRENCY_USD_ENABLED: bool = False  # Feature flag for gradual rollout
    DEFAULT_LANGUAGE: str = "ar"
    SUPPORTED_LANGUAGES: str = '[" ar","en"]'
    
    @property
    def supported_currencies_list(self) -> List[str]:
        return json.loads(self.SUPPORTED_CURRENCIES)
    
    @property
    def supported_languages_list(self) -> List[str]:
        return json.loads(self.SUPPORTED_LANGUAGES)
    
    # Tax
    DEFAULT_TAX_RATE: float = 14.0
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = [".env", "backend/.env"]
        case_sensitive = True
        extra = "ignore"


settings = Settings()