"""
Configuration management for the music app backend.
Centralizes all environment variables and provides validation.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Database
    database_url: str = Field(..., env='DATABASE_URL')
    supabase_url: str = Field(..., env='SUPABASE_URL')
    supabase_key: str = Field(..., env='SUPABASE_KEY')
    
    # Cloudflare R2
    r2_access_key: str = Field(..., env='R2_ACCESS_KEY')
    r2_secret_key: str = Field(..., env='R2_SECRET_KEY')
    r2_audio_bucket: str = Field(..., env='R2_AUDIO_BUCKET')
    r2_image_bucket: str = Field(..., env='R2_IMAGE_BUCKET')
    r2_endpoint: str = Field(..., env='R2_ENDPOINT')
    
    # Application
    app_name: str = "Music Sharing API"
    debug: bool = Field(False, env='DEBUG')
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # Authentication
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production", 
        env='SECRET_KEY'
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    
    # File upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_audio_formats: list[str] = [".mp3", ".wav", ".flac", ".aac", ".ogg"]
    allowed_image_formats: list[str] = [".jpg", ".jpeg", ".png", ".webp"]
    
    # Signed URL expiration (in seconds)
    signed_url_expiration: int = 3600  # 1 hour
    
    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v):
        if not v:
            raise ValueError('SUPABASE_URL is required')
        if not v.startswith('https://'):
            raise ValueError('SUPABASE_URL must be a valid HTTPS URL')
        return v
    
    @field_validator('r2_endpoint')
    @classmethod
    def validate_r2_endpoint(cls, v):
        if not v:
            raise ValueError('R2_ENDPOINT is required')
        if not v.startswith('https://'):
            raise ValueError('R2_ENDPOINT must be a valid HTTPS URL')
        return v

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "forbid"
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
