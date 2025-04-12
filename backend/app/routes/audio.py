import httpx
import logging
import tempfile
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi import UploadFile, File, Form
from app.crud import get_audio, list_audio, create_audio
from app.schemas import AudioFileCreate
from app.services.r2_service import upload_to_r2, generate_signed_url
from app.services.ml import analyze_audio


# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_IMAGE_URL = ""

@router.post("/audio/upload/")
async def upload_audio(
    file: UploadFile = File(...),
    image: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    artist: Optional[str] = Form(None)
):
    """Uploads an audio file (and optional image) to Cloudflare R2 and stores metadata in Supabase."""

    # Save the uploaded file locally
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(await file.read())
        temp_path = temp_audio.name

    # Analyze it
    features = analyze_audio(temp_path)

    # Then rewind the file so it can be re-used
    file.file.seek(0)

    # Upload audio file
    file_url = upload_to_r2(file)

    # Upload image if provided, otherwise use default
    image_url = upload_to_r2(image, is_audio=False) if image else DEFAULT_IMAGE_URL
    
    if not title:
        title = file.filename
    if not artist:
        artist = "Unknown Artist"

    # Build audio metadata
    audio_data = AudioFileCreate(
        title=file.filename,
        artist=artist,
        file_url=file_url,
        image_url=image_url,
        bpm=features.get("bpm"),
        key=features.get("key"),
        scale=features.get("scale")
    )
    
    return create_audio(audio_data)

@router.post("/audio/analyze/")
async def analyze_uploaded_audio(file: UploadFile = File(...)):
    """
    Test route: Accepts a single audio file,
    runs Essentia analysis, and returns musical features.
    """
    import tempfile
    from app.services.ml import analyze_audio

    # Save uploaded audio to temp file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(await file.read())
            temp_path = temp_audio.name

        # Run Essentia analysis
        features = analyze_audio(temp_path)

        return {
            "filename": file.filename,
            "features": features
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/audio/{audio_id}")
async def get_audio_metadata(audio_id: int):
    """Fetch metadata for a specific audio file by ID."""
    logger.info(f"🔹 API called for ID: {audio_id}")

    audio_data = get_audio(audio_id)

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
