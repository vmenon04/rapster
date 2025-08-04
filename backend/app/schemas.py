from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


# User Authentication Schemas
class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError('Username must contain only letters, numbers, underscores, and hyphens')
        return v.lower()


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, description="User password")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(UserBase):
    """Schema for returning user data."""
    id: str = Field(..., description="User ID")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether user email is verified")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    bio: Optional[str] = Field(None, description="User bio")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    upload_count: Optional[int] = Field(None, description="Number of tracks uploaded")

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication tokens."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenData(BaseModel):
    """Schema for token payload."""
    user_id: Optional[str] = None
    email: Optional[str] = None


class AudioFileBase(BaseModel):
    """Base schema for audio file data."""
    title: str = Field(..., min_length=1, max_length=255, description="Track title")
    artist: str = Field(..., min_length=1, max_length=255, description="Artist name")
    
    @validator('title', 'artist')
    def validate_strings(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty or whitespace only')
        return v.strip()


class AudioFileCreate(AudioFileBase):
    """Schema for creating new audio file records."""
    file_url: str = Field(..., description="Primary audio file URL")
    image_url: Optional[str] = Field(None, description="URL to the cover image")
    
    # Multi-format support
    file_urls: Optional[Dict[str, str]] = Field(None, description="URLs for different audio qualities/formats")
    hls_url: Optional[str] = Field(None, description="URL to HLS master playlist")
    formats_available: Optional[List[str]] = Field(None, description="Available audio formats")
    
    # Musical analysis features
    bpm: Optional[float] = Field(None, ge=0, le=300, description="Beats per minute")
    key: Optional[str] = Field(None, max_length=10, description="Musical key")
    scale: Optional[str] = Field(None, max_length=20, description="Musical scale")
    key_strength: Optional[float] = Field(None, ge=0, le=1.2, description="Key detection confidence")
    
    # Audio characteristics
    duration_sec: Optional[float] = Field(None, ge=0, description="Duration in seconds")
    loudness: Optional[float] = Field(None, description="Loudness in LUFS")
    danceability: Optional[float] = Field(None, ge=0, le=1.5, description="Danceability score")
    energy: Optional[float] = Field(None, ge=0, le=1.5, description="Energy level")
    
    # Advanced features
    mfcc: Optional[List[float]] = Field(None, description="MFCC coefficients")
    spectral_contrast: Optional[List[float]] = Field(None, description="Spectral contrast")
    zero_crossing_rate: Optional[float] = Field(None, ge=0, description="Zero crossing rate")
    silence_rate: Optional[float] = Field(None, ge=0, le=1, description="Silence rate")
    
    @validator('file_url', 'image_url', 'hls_url')
    def validate_urls(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URLs must start with http:// or https://')
        return v
    
    @validator('danceability', 'energy', 'key_strength', pre=True)
    def clamp_values(cls, v):
        """Clamp values that might exceed expected ranges due to analysis variations."""
        if v is not None:
            # Clamp values to reasonable ranges
            if isinstance(v, (int, float)):
                return max(0, min(v, 1.5))  # Allow up to 1.5 for flexibility
        return v


class AudioFileResponse(AudioFileBase):
    """Schema for returning audio file data."""
    id: int = Field(..., description="Unique identifier")
    user_id: str = Field(..., description="ID of the user who uploaded the track")
    uploader_username: Optional[str] = Field(None, description="Username of the uploader")
    file_url: str = Field(..., description="Signed URL to the audio file")
    image_url: Optional[str] = Field(None, description="Signed URL to the cover image")
    
    # Multi-format support
    file_urls: Optional[Dict[str, str]] = Field(None, description="Signed URLs for different qualities/formats")
    hls_url: Optional[str] = Field(None, description="Signed URL to HLS master playlist")
    formats_available: Optional[List[str]] = Field(None, description="Available audio formats")
    
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Include all analysis features
    bpm: Optional[float] = None
    key: Optional[str] = None
    scale: Optional[str] = None
    key_strength: Optional[float] = None
    duration_sec: Optional[float] = None
    loudness: Optional[float] = None
    danceability: Optional[float] = None
    energy: Optional[float] = None
    mfcc: Optional[List[float]] = None
    spectral_contrast: Optional[List[float]] = None
    zero_crossing_rate: Optional[float] = None
    silence_rate: Optional[float] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat() if dt else None
        }


class AudioAnalysisResponse(BaseModel):
    """Schema for audio analysis results."""
    filename: str = Field(..., description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    analysis_successful: bool = Field(..., description="Whether analysis completed successfully")
    features: dict = Field(..., description="Extracted audio features")
    
    
class HealthCheckResponse(BaseModel):
    """Schema for health check response."""
    status: str = Field(..., description="Service status")
    database_accessible: bool = Field(..., description="Database connectivity status")
    analysis_available: bool = Field(..., description="Audio analysis availability")
    total_files: int = Field(..., description="Total number of files in database")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")