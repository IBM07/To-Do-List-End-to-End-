# ===========================================
# AuraTask Configuration
# ===========================================
# Uses pydantic-settings to load environment variables

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses .env file in the backend directory.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ===========================================
    # Database (MySQL)
    # ===========================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "auratask"
    DB_USER: str = "root"  # Default MySQL user
    DB_PASSWORD: str  # REQUIRED - must be set in .env
    
    # ===========================================
    # Redis (Cache & Celery Broker)
    # ===========================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str  # REQUIRED - must be set in .env
    
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL from components."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # ===========================================
    # JWT Authentication
    # ===========================================
    SECRET_KEY: str  # REQUIRED - must be set in .env (generate with secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ===========================================
    # SMTP Settings (Gmail)
    # ===========================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_NAME: str = "AuraTask"
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # ===========================================
    # Telegram (Optional)
    # ===========================================
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    
    # ===========================================
    # Discord (Optional)
    # ===========================================
    DISCORD_WEBHOOK_URL: Optional[str] = None
    
    # ===========================================
    # Groq AI (for NLP parsing)
    # ===========================================
    GROQ_API_KEY: Optional[str] = None
    
    # ===========================================
    # Encryption (for sensitive user data)
    # ===========================================
    # Fernet key for encrypting telegram_chat_id, discord_webhook_url
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: Optional[str] = None
    
    # ===========================================
    # Application Settings
    # ===========================================
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # ===========================================
    # CORS Settings
    # ===========================================
    # Comma-separated list of allowed origins for production
    # Example: "https://auratask.com,https://www.auratask.com"
    CORS_ORIGINS: str = "http://localhost:3000"  # Default for development
    
    @property
    def get_cors_origins(self) -> list:
        """Get CORS origins as a list based on environment."""
        if self.ENVIRONMENT == "development":
            return ["*"]  # Allow all in development
        # In production, parse comma-separated origins
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    def model_post_init(self, __context) -> None:
        """Called after model initialization - validate production settings."""
        self.validate_production_settings()
    
    def validate_production_settings(self) -> None:
        """
        Validate critical settings when running in production.
        
        Raises ValueError if production requirements are not met.
        """
        if self.ENVIRONMENT != "production":
            return  # Skip validation in development
        
        errors = []
        
        # Check SECRET_KEY is changed from default
        if "change-in-production" in self.SECRET_KEY.lower():
            errors.append("SECRET_KEY must be changed for production")
        
        # Require ENCRYPTION_KEY in production
        if not self.ENCRYPTION_KEY:
            errors.append("ENCRYPTION_KEY is required in production")
        
        # DEBUG must be False in production
        if self.DEBUG:
            errors.append("DEBUG must be False in production")
        
        if errors:
            error_msg = "Production configuration errors:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ValueError(error_msg)
    
    # ===========================================
    # Database URLs (Computed Properties)
    # ===========================================
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Async MySQL URL for FastAPI (aiomysql driver)."""
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+aiomysql://{self.DB_USER}:{encoded_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Sync MySQL URL for Celery workers (pymysql driver)."""
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{self.DB_USER}:{encoded_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    Use this function to access settings throughout the app.
    """
    return Settings()


# Convenience export
settings = get_settings()
