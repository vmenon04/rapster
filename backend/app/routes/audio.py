import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi import UploadFile, File
from app.crud import get_audio, list_audio, create_audio
from app.schemas import AudioFileCreate
from app.services.r2_service import upload_to_r2, generate_signed_url
import os

# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_IMAGE_URL = ""

@router.post("/audio/upload/")
async def upload_audio(
    file: UploadFile = File(...),
    image: UploadFile = File(None),  # ✅ Optional image upload
):
    """Uploads an audio file (and optional image) to Cloudflare R2 and stores metadata in Supabase."""

    # Upload audio file
    file_url = upload_to_r2(file)

    # Upload image if provided, otherwise use default
    image_url = upload_to_r2(image, is_audio=False) if image else DEFAULT_IMAGE_URL

    # Create metadata entry
    audio_data = AudioFileCreate(
        title=file.filename, 
        artist="Unknown", 
        file_url=file_url, 
        image_url=image_url
    )
    
    return create_audio(audio_data)

@router.get("/audio/{audio_id}")
async def get_audio_metadata(audio_id: int):
    """Fetch metadata for a specific audio file by ID."""
    logger.info(f"🔹 API called for ID: {audio_id}")

    audio_data = get_audio(audio_id, is_audio=False)

    if not audio_data:
        logger.warning(f"⚠️ Audio file with ID {audio_id} not found!")
        raise HTTPException(status_code=404, detail="Audio file not found in Supabase")

    logger.info(f"✅ Audio file retrieved: {audio_data}")
    return audio_data

@router.get("/audio/list-audio/")
async def list_all_audio():
    """Fetch metadata for all stored audio files."""
    logger.info("📋 Fetching all audio files from Supabase")

    audio_files = list_audio()

    if not audio_files:
        logger.warning("⚠️ No audio files found!")
        return {"message": "No audio files available"}

    logger.info(f"✅ Retrieved {len(audio_files)} audio files")
    return audio_files

@router.get("/audio/get-signed-url/{audio_id}")
async def get_signed_url(audio_id: int):
    """Generate a new signed URL when a user requests a track"""
    audio = get_audio(audio_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # ✅ Extract ONLY the file path (exclude query parameters)
    file_url = audio["file_url"]
    image_url = audio["image_url"]

    file_key = file_url.split("/")[-1].split("?")[0]  # ✅ Remove query params
    image_key = image_url.split("/")[-1].split("?")[0]

    print(f"🔍 Corrected File Key: {file_key}")  # ✅ Debugging output

    signed_audio_url = generate_signed_url(os.getenv("R2_AUDIO_BUCKET"), file_key)
    signed_image_url = generate_signed_url(os.getenv("R2_IMAGE_BUCKET"), image_key)

    return {"signed_audio_url": signed_audio_url, "signed_image_url": signed_image_url}
