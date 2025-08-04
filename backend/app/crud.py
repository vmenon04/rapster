from app.schemas import AudioFileCreate, UserCreate
from app.models import User, AudioFile
from app.services.r2_service import generate_signed_url
from app.config import get_settings
from app.logger import get_logger
from app.exceptions import DatabaseError, ValidationError
from app.auth import get_password_hash
from supabase import create_client
from typing import List, Optional, Dict, Any
import time
import asyncio
from functools import wraps
import uuid
from concurrent.futures import ThreadPoolExecutor

settings = get_settings()
logger = get_logger("crud")

# Initialize Supabase client
supabase_client = create_client(settings.supabase_url, settings.supabase_key)

# Thread pool for async execution of sync operations
_thread_pool = ThreadPoolExecutor(max_workers=10)


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry database operations on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise DatabaseError(f"Operation failed after {max_retries} attempts", str(last_exception))
        return wrapper
    return decorator


def async_retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Async decorator to retry database operations on failure."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise DatabaseError(f"Operation failed after {max_retries} attempts", str(last_exception))
        return wrapper
    return decorator


def run_in_thread(func):
    """Run a sync function in a thread pool."""
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_thread_pool, func, *args, **kwargs)
    return wrapper


def validate_audio_data(audio: AudioFileCreate) -> None:
    """Validate audio file data before database operations."""
    if not audio.title or not audio.title.strip():
        raise ValidationError("Title is required and cannot be empty")
    
    if not audio.artist or not audio.artist.strip():
        raise ValidationError("Artist is required and cannot be empty")
    
    if not audio.file_url or not audio.file_url.strip():
        raise ValidationError("File URL is required and cannot be empty")


# User CRUD Operations
@retry_on_failure()
def create_user(user_data: UserCreate) -> User:
    """Create a new user in the database."""
    try:
        # Check if user already exists
        existing_user = get_user_by_email(user_data.email)
        if existing_user:
            raise ValidationError("User with this email already exists")
        
        existing_username = get_user_by_username(user_data.username)
        if existing_username:
            raise ValidationError("Username already taken")
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Prepare user data
        user_dict = {
            "id": str(uuid.uuid4()),
            "email": user_data.email,
            "username": user_data.username.lower(),
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "bio": user_data.bio,
            "is_active": True,
            "is_verified": False,
        }
        
        # Insert into database
        result = supabase_client.table("users").insert(user_dict).execute()
        
        if not result.data:
            raise DatabaseError("Failed to create user", "No data returned from insert")
        
        logger.info(f"Created user: {user_data.email}")
        return User(**result.data[0])
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise DatabaseError("Failed to create user", str(e))


@retry_on_failure()
def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email address."""
    try:
        result = supabase_client.table("users").select("*").eq("email", email).execute()
        
        if result.data:
            return User(**result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"Error fetching user by email: {e}")
        raise DatabaseError("Failed to fetch user", str(e))


@retry_on_failure()
def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username."""
    try:
        result = supabase_client.table("users").select("*").eq("username", username.lower()).execute()
        
        if result.data:
            return User(**result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"Error fetching user by username: {e}")
        raise DatabaseError("Failed to fetch user", str(e))


@retry_on_failure()
def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID."""
    try:
        result = supabase_client.table("users").select("*").eq("id", user_id).execute()
        
        if result.data:
            return User(**result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"Error fetching user by ID: {e}")
        raise DatabaseError("Failed to fetch user", str(e))


# Async versions of user CRUD operations
@async_retry_on_failure()
async def get_user_by_id_async(user_id: str) -> Optional[User]:
    """Async version of get_user_by_id."""
    return await run_in_thread(get_user_by_id)(user_id)


@async_retry_on_failure()
async def get_user_by_email_async(email: str) -> Optional[User]:
    """Async version of get_user_by_email."""
    return await run_in_thread(get_user_by_email)(email)


@async_retry_on_failure()
async def get_user_by_username_async(username: str) -> Optional[User]:
    """Async version of get_user_by_username."""
    return await run_in_thread(get_user_by_username)(username)


@async_retry_on_failure()
async def create_user_async(user_data: UserCreate) -> User:
    """Async version of create_user."""
    return await run_in_thread(create_user)(user_data)


# Audio CRUD Operations (Updated for User Authentication)
@retry_on_failure(max_retries=3)
def create_audio(audio: AudioFileCreate, user_id: str) -> Optional[Dict[Any, Any]]:
    """Store metadata in Supabase with validation and retry logic."""
    try:
        # Validate input data
        validate_audio_data(audio)
        
        logger.info(f"Creating audio record for: {audio.title} by {audio.artist} (user: {user_id})")
        
        # Prepare data for insertion
        audio_data = {
            "title": audio.title.strip(),
            "artist": audio.artist.strip(),
            "user_id": user_id,
            "file_url": audio.file_url,
            "image_url": audio.image_url,
            "bpm": audio.bpm,
            "key": audio.key,
            "scale": audio.scale,
            "key_strength": audio.key_strength,
            "duration_sec": audio.duration_sec,
            "loudness": audio.loudness,
            "danceability": audio.danceability,
            "energy": audio.energy,
            "mfcc": audio.mfcc,
            "spectral_contrast": audio.spectral_contrast,
            "zero_crossing_rate": audio.zero_crossing_rate,
            "silence_rate": audio.silence_rate,
        }
        
        # Remove None values
        audio_data = {k: v for k, v in audio_data.items() if v is not None}
        
        result = supabase_client.table("audio_files").insert(audio_data).execute()

        if not result.data:
            raise DatabaseError("Failed to insert audio record - no data returned")

        record = result.data[0]
        logger.info(f"Successfully created audio record with ID: {record.get('id')}")
        return record

    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Failed to create audio record: {e}")
        raise DatabaseError(f"Failed to create audio record: {str(e)}")


@retry_on_failure(max_retries=3)
def get_audio(audio_id: int) -> Optional[Dict[Any, Any]]:
    """Retrieve audio metadata from Supabase with signed URLs."""
    try:
        if audio_id <= 0:
            raise ValidationError("Audio ID must be a positive integer")
            
        logger.info(f"Fetching audio record with ID: {audio_id}")
        
        # Join with users table to get uploader info
        response = supabase_client.table("audio_files").select(
            "*, users!audio_files_user_id_fkey(username, full_name)"
        ).eq("id", audio_id).execute()
        
        if not response.data:
            logger.warning(f"No audio file found with ID: {audio_id}")
            return None
            
        audio = response.data[0]
        
        # Add uploader info
        if audio.get("users"):
            audio["uploader_username"] = audio["users"]["username"]
            audio["uploader_full_name"] = audio["users"]["full_name"]
        
        # Generate signed URLs for file access
        if "file_url" in audio and audio["file_url"]:
            file_key = audio["file_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params
            audio["file_url"] = generate_signed_url(settings.r2_audio_bucket, file_key)
            
        if "image_url" in audio and audio["image_url"]:
            image_key = audio["image_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params  
            audio["image_url"] = generate_signed_url(settings.r2_image_bucket, image_key)
        
        logger.info(f"Successfully retrieved audio file: {audio['title']}")
        return audio
        
    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Failed to retrieve audio file {audio_id}: {e}")
        raise DatabaseError(f"Failed to retrieve audio file: {str(e)}")


@retry_on_failure(max_retries=3)
def list_audio() -> List[Dict[Any, Any]]:
    """Retrieve all audio metadata from Supabase with signed URLs."""
    try:
        logger.info("Fetching all audio files from database")
        
        # Join with users table to get uploader info
        response = supabase_client.table("audio_files").select(
            "*, users!audio_files_user_id_fkey(username, full_name)"
        ).order("created_at", desc=True).execute()
        
        if not response.data:
            logger.info("No audio files found in database")
            return []
        
        # Generate signed URLs for all files and add uploader info
        for audio in response.data:
            # Add uploader info
            if audio.get("users"):
                audio["uploader_username"] = audio["users"]["username"]
                audio["uploader_full_name"] = audio["users"]["full_name"]
            
            if "file_url" in audio and audio["file_url"]:
                file_key = audio["file_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params
                audio["file_url"] = generate_signed_url(settings.r2_audio_bucket, file_key)
                
            if "image_url" in audio and audio["image_url"]:
                image_key = audio["image_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params
                audio["image_url"] = generate_signed_url(settings.r2_image_bucket, image_key)
            
        logger.info(f"Successfully retrieved {len(response.data)} audio files")
        return response.data
        
    except Exception as e:
        logger.error(f"Failed to list audio files: {e}")
        raise DatabaseError(f"Failed to list audio files: {str(e)}")


def delete_audio(audio_id: int) -> bool:
    """Delete an audio record from the database."""
    try:
        if audio_id <= 0:
            raise ValidationError("Audio ID must be a positive integer")
            
        logger.info(f"Deleting audio record with ID: {audio_id}")
        
        response = supabase_client.table("audio_files").delete().eq("id", audio_id).execute()
        
        if not response.data:
            logger.warning(f"No audio file found with ID: {audio_id}")
            return False
            
        logger.info(f"Successfully deleted audio record with ID: {audio_id}")
        return True
        
    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Failed to delete audio file {audio_id}: {e}")
        raise DatabaseError(f"Failed to delete audio file: {str(e)}")


def get_audio(audio_id: int) -> Optional[Dict[Any, Any]]:
    """Retrieve audio metadata from Supabase with signed URLs"""
    try:
        logger.info(f"🔍 Fetching audio ID: {audio_id}")
        
        response = supabase_client.table("audio_files").select("*").eq("id", audio_id).execute()
        
        if not response.data:
            logger.warning(f"⚠️ No audio file found with ID: {audio_id}")
            return None
            
        audio = response.data[0]
        
        # Generate signed URLs for file access
        if "file_url" in audio and audio["file_url"]:
            file_key = audio["file_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params
            audio["file_url"] = generate_signed_url(settings.r2_audio_bucket, file_key)
            
        if "image_url" in audio and audio["image_url"]:
            image_key = audio["image_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params  
            audio["image_url"] = generate_signed_url(settings.r2_image_bucket, image_key)
        
        logger.info(f"✅ Successfully retrieved audio file: {audio['title']}")
        return audio
        
    except Exception as e:
        logger.error(f"Failed to retrieve audio file {audio_id}: {e}")
        raise Exception(f"Database Error: {e}")


def list_audio() -> List[Dict[Any, Any]]:
    """Retrieve all audio metadata from Supabase with signed URLs"""
    try:
        logger.info("� Fetching all audio files from Supabase")
        
        response = supabase_client.table("audio_files").select("*").execute()
        
        if not response.data:
            logger.info("No audio files found in database")
            return []
        
        # Generate signed URLs for all files
        for audio in response.data:
            if "file_url" in audio and audio["file_url"]:
                file_key = audio["file_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params
                audio["file_url"] = generate_signed_url(settings.r2_audio_bucket, file_key)
                
            if "image_url" in audio and audio["image_url"]:
                image_key = audio["image_url"].split("/")[-1].split("?")[0]  # Extract file key, remove query params
                audio["image_url"] = generate_signed_url(settings.r2_image_bucket, image_key)
            
        logger.info(f"✅ Retrieved {len(response.data)} audio files")
        return response.data
        
    except Exception as e:
        logger.error(f"Failed to list audio files: {e}")
        raise Exception(f"Database Error: {e}")