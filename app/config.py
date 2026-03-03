from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    
    # Telegram
    USER_BOT_TOKEN: str
    ADMIN_BOT_TOKEN: str
    TELEGRAM_ADMIN_CHAT_ID: str
    TELEGRAM_ORDER_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ORDER_CHANNEL_ID: Optional[str] = None
    
    # File Upload
    UPLOAD_DIR: str = os.path.join(os.getcwd(), "uploads")
    MAX_UPLOAD_SIZE: int = 5242880  # 5MB
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # App
    APP_NAME: str = "Taxi Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = []
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = None

    # CLICK (Uzbekistan) payment integration
    CLICK_SERVICE_ID: Optional[int] = None
    CLICK_MERCHANT_ID: Optional[int] = None
    CLICK_SECRET_KEY: Optional[str] = None
    CLICK_MERCHANT_USER_ID: Optional[int] = None
    CLICK_ALLOWED_IPS: Optional[str] = None
    CLICK_VERIFY_SIGNATURE: Optional[bool] = None
    CLICK_DISABLE_SIGN_CHECK: Optional[bool] = None

    # Firebase Cloud Messaging
    FCM_ENABLED: bool = True
    FCM_PROJECT_ID: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    SERVICE_ACCOUNT_JSON_PATH: Optional[str] = None
    FCM_SERVICE_ACCOUNT_FILE: Optional[str] = None
    FCM_SERVICE_ACCOUNT_JSON: Optional[str] = None

    # Eskiz SMS
    ESKIZ_EMAIL: Optional[str] = None
    ESKIZ_SECRET: Optional[str] = None
    ESKIZ_BASE_URL: str = "https://notify.eskiz.uz/api"
    ESKIZ_FROM: Optional[str] = None

    # OTP
    OTP_SALT: str = "change-this-otp-salt"
    OTP_EXPIRE_SECONDS: int = 120
    OTP_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 5

    # HTTP
    HTTP_TIMEOUT_SECONDS: int = 10

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value or []
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
