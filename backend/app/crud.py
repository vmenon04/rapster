from app.schemas import AudioFileCreate
from app.services.r2_service import generate_signed_url
import os
from dotenv import load_dotenv
from supabase import create_client
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_audio(audio):
    """Store metadata in Supabase only"""
    data, error = supabase_client.table("audio_files").insert({
        "title": audio.title,
        "artist": audio.artist,
        "file_url": audio.file_url,
        "image_url": audio.image_url,
        "bpm": audio.bpm,
        "key": audio.key,
        "scale": audio.scale,
    }).execute()


    print(f"Supabase Response: {data}, Error: {error}")  # Debugging output

    if error and error != ('count', None):  # ✅ Ignore the "count: None" response
        raise Exception(f"Supabase Error: {error}")

    return data[1] if data else None


def get_audio(audio_id: int):
    """Retrieve audio metadata from Supabase with a signed URL"""
    logger.info(f"🔍 Fetching audio ID: {audio_id}")

    response = supabase_client.table("audio_files").select("*").eq("id", audio_id).execute()

    if not response.data:
        logger.warning(f"⚠️ No data found for audio ID {audio_id}!")
        return None

    audio = response.data[0]
    if "file_url" in audio:
        file_key = audio["file_url"].split("/")[-1]  # Extract file key
        audio["file_url"] = generate_signed_url(os.getenv("R2_AUDIO_BUCKET"), file_key)  # Replace with signed URL
    if "image_url" in audio:
        image_key = audio["image_url"].split("/")[-1]  # Extract file key
        audio["image_url"] = generate_signed_url(os.getenv("R2_IMAGE_BUCKET"), image_key)  # Replace with signed URL

    return audio



def list_audio():
    """List all audio files from Supabase and generate signed URLs"""
    response = supabase_client.table("audio_files").select("*").execute()

    if not response.data:
        return []

    # ✅ Replace the `file_url` with a signed URL before returning
    for audio in response.data:
        if "file_url" in audio:
            file_key = audio["file_url"].split("/")[-1]  # Extract file key from URL
            audio["file_url"] = generate_signed_url(os.getenv("R2_AUDIO_BUCKET"), file_key)
        if "image_url" in audio and audio["image_url"]:
            image_key = audio["image_url"].split("/")[-1]  # Extract file key
            audio["image_url"] = generate_signed_url(os.getenv("R2_IMAGE_BUCKET"), image_key)

    return response.data