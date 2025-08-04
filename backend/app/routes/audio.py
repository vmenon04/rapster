import tempfile
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.crud import get_audio, list_audio, create_audio, delete_audio
from app.schemas import AudioFileCreate, AudioFileResponse
from app.models import User
from app.services.r2_service import upload_to_r2, generate_signed_url
from app.services.ml import analyze_audio, get_analysis_metadata
from app.dependencies import get_current_user, get_current_user_optional, rate_limit_upload, rate_limit_normal
from app.config import get_settings
from app.logger import get_logger
from app.exceptions import (
    DatabaseError, FileUploadError, AudioAnalysisError, 
    ValidationError, ExternalServiceError
)

settings = get_settings()
logger = get_logger("audio_routes")

# Initialize router
router = APIRouter(prefix="/audio", tags=["audio"])

DEFAULT_IMAGE_URL = ""


@router.get("/health")
async def health_check(_: None = Depends(rate_limit_normal)):  # Rate limit for testing
    """Health check endpoint for the audio service."""
    try:
        # Test database connectivity
        test_files = list_audio()
        
        # Test analysis capabilities
        analysis_meta = get_analysis_metadata()
        
        return {
            "status": "healthy",
            "database_accessible": True,
            "analysis_available": analysis_meta["essentia_available"],
            "total_files": len(test_files) if isinstance(test_files, list) else 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@router.post("/upload/", response_model=dict)
async def upload_audio(
    file: UploadFile = File(..., description="Audio file to upload"),
    image: Optional[UploadFile] = File(None, description="Optional cover image"),
    title: Optional[str] = Form(None, description="Track title"),
    artist: Optional[str] = Form(None, description="Artist name"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_upload)  # Rate limit: 10 uploads per 5 minutes
):
    """
    Upload an audio file with optional cover image to cloud storage and analyze it.
    Requires user authentication.
    
    This endpoint:
    1. Validates the uploaded files
    2. Analyzes the audio for musical features
    3. Uploads files to R2 storage
    4. Stores metadata in the database
    """
    temp_audio_path = None
    
    try:
        logger.info(f"Starting upload process for file: {file.filename} by user: {current_user.username}")
        
        # Validate required file
        if not file or not file.filename:
            raise ValidationError("Audio file is required")
        
        # Create temporary file for analysis
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        # Reset file pointer for upload
        file.file.seek(0)
        
        # Analyze audio features
        logger.info("Analyzing audio features...")
        try:
            features = analyze_audio(temp_audio_path)
            logger.info(f"Analysis completed: BPM={features.get('bpm')}, Key={features.get('key')}")
        except AudioAnalysisError as e:
            logger.warning(f"Audio analysis failed: {e}")
            # Continue with upload even if analysis fails
            features = {}
        
        # Upload files to R2
        logger.info("Uploading files to cloud storage...")
        try:
            file_url = upload_to_r2(file, is_audio=True)
            if not file_url:
                raise FileUploadError("Failed to upload audio file to cloud storage")
            
            image_url = DEFAULT_IMAGE_URL
            if image:
                image_url = upload_to_r2(image, is_audio=False)
                if not image_url:
                    logger.warning("Failed to upload image, using default")
                    image_url = DEFAULT_IMAGE_URL
                    
        except FileUploadError:
            raise
        except Exception as e:
            raise FileUploadError(f"Unexpected error during file upload: {str(e)}")
        
        # Prepare metadata
        final_title = title.strip() if title else file.filename
        final_artist = artist.strip() if artist else "Unknown Artist"
        
        # Create database record
        audio_data = AudioFileCreate(
            title=final_title,
            artist=final_artist,
            file_url=file_url,
            image_url=image_url,
            bpm=features.get("bpm"),
            key=features.get("key"),
            scale=features.get("scale"),
            key_strength=features.get("key_strength"),
            duration_sec=features.get("duration_sec"),
            loudness=features.get("loudness"),
            danceability=features.get("danceability"),
            energy=features.get("energy"),
        )
        
        try:
            result = create_audio(audio_data, current_user.id)
            if not result:
                raise DatabaseError("Failed to create database record")
                
            logger.info(f"Successfully uploaded and processed: {final_title} by user: {current_user.username}")
            return {
                "message": "Upload successful",
                "id": result.get("id"),
                "title": final_title,
                "artist": final_artist,
                "uploader": current_user.username,
                "features": features
            }
            
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected database error: {str(e)}")
    
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileUploadError as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during upload")
    
    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
                logger.debug(f"Cleaned up temporary file: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")

@router.post("/analyze/", response_model=dict)
async def analyze_uploaded_audio(
    file: UploadFile = File(..., description="Audio file to analyze")
):
    """
    Analyze an audio file for musical features without storing it.
    
    This is a test/preview endpoint that only performs analysis
    without uploading to storage or saving to database.
    """
    temp_audio_path = None
    
    try:
        logger.info(f"Starting analysis for file: {file.filename}")
        
        if not file or not file.filename:
            raise ValidationError("Audio file is required")
        
        # Save uploaded audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name

        # Run analysis
        try:
            features = analyze_audio(temp_audio_path)
            logger.info(f"Analysis completed for {file.filename}")
            
            return {
                "filename": file.filename,
                "file_size": len(content),
                "analysis_successful": True,
                "features": features
            }
            
        except AudioAnalysisError as e:
            logger.error(f"Analysis failed for {file.filename}: {e}")
            raise HTTPException(status_code=422, detail=f"Audio analysis failed: {str(e)}")

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during analysis")
    
    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
                logger.debug(f"Cleaned up temporary file: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")


@router.get("/{audio_id}", response_model=dict)
async def get_audio_metadata(audio_id: int, _: None = Depends(rate_limit_normal)):  # Rate limit: 100 requests per minute
    """Get metadata for a specific audio file by ID."""
    try:
        logger.info(f"Fetching metadata for audio ID: {audio_id}")

        if audio_id <= 0:
            raise ValidationError("Audio ID must be a positive integer")

        audio_data = get_audio(audio_id)

        if not audio_data:
            logger.warning(f"Audio file with ID {audio_id} not found")
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file with ID {audio_id} not found"
            )

        logger.info(f"Successfully retrieved metadata for audio ID: {audio_id}")
        return audio_data

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list-audio/", response_model=list)
async def list_all_audio(_: None = Depends(rate_limit_normal)):  # Rate limit: 100 requests per minute
    """Get metadata for all stored audio files."""
    try:
        logger.info("Fetching all audio files")
        
        audio_files = list_audio()
        
        if not audio_files:
            logger.info("No audio files found")
            return []

        logger.info(f"Successfully retrieved {len(audio_files)} audio files")
        return audio_files

    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{audio_id}", response_model=dict)
async def delete_audio_file(audio_id: int, current_user: User = Depends(get_current_user)):
    """Delete an audio file and its metadata. Only the uploader can delete their files."""
    try:
        logger.info(f"Delete request for audio file {audio_id} by user: {current_user.username}")
        
        # First check if the audio file exists and get its details
        audio_data = get_audio(audio_id)
        if not audio_data:
            raise HTTPException(
                status_code=404,
                detail=f"Audio file with ID {audio_id} not found"
            )
        
        # Check if the current user owns this audio file
        if audio_data.get("user_id") != current_user.id:
            logger.warning(f"User {current_user.username} attempted to delete audio {audio_id} owned by another user")
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own uploads"
            )
        
        if audio_id <= 0:
            raise ValidationError("Audio ID must be a positive integer")
        
        # First, get the file metadata to find the file URLs
        audio_data = get_audio(audio_id)
        if not audio_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file with ID {audio_id} not found"
            )
        
        # Delete from database
        success = delete_audio(audio_id)
        if not success:
            raise DatabaseError("Failed to delete audio record from database")
        
        # TODO: Also delete files from R2 storage
        # This would require extracting file keys from URLs and calling delete_file_from_r2
        
        logger.info(f"Successfully deleted audio file with ID: {audio_id}")
        return {
            "message": f"Audio file {audio_id} deleted successfully",
            "deleted_id": audio_id
        }
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/get-signed-url/{audio_id}", response_model=dict)
async def get_signed_url_endpoint(audio_id: int):
    """Generate new signed URLs for an audio file."""
    try:
        logger.info(f"Generating signed URLs for audio ID: {audio_id}")
        
        if audio_id <= 0:
            raise ValidationError("Audio ID must be a positive integer")
        
        audio = get_audio(audio_id)
        if not audio:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file with ID {audio_id} not found"
            )

        # Extract file keys from URLs (remove query parameters)
        file_url = audio.get("file_url", "")
        image_url = audio.get("image_url", "")
        
        if not file_url:
            raise ExternalServiceError("No file URL found for this audio record")

        file_key = file_url.split("/")[-1].split("?")[0]
        
        try:
            signed_audio_url = generate_signed_url(settings.r2_audio_bucket, file_key)
            if not signed_audio_url:
                raise ExternalServiceError("Failed to generate signed URL for audio file")
                
            result = {"signed_audio_url": signed_audio_url}
            
            # Generate signed URL for image if available
            if image_url and image_url != DEFAULT_IMAGE_URL:
                image_key = image_url.split("/")[-1].split("?")[0]
                signed_image_url = generate_signed_url(settings.r2_image_bucket, image_key)
                if signed_image_url:
                    result["signed_image_url"] = signed_image_url
            
            logger.info(f"Successfully generated signed URLs for audio ID: {audio_id}")
            return result
            
        except Exception as e:
            raise ExternalServiceError(f"Failed to generate signed URLs: {str(e)}")

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ExternalServiceError as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analysis/metadata", response_model=dict)
async def get_analysis_capabilities():
    """Get information about available analysis capabilities."""
    try:
        metadata = get_analysis_metadata()
        return {
            "analysis_service": "Essentia",
            "capabilities": metadata
        }
    except Exception as e:
        logger.error(f"Error getting analysis metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analysis metadata")
